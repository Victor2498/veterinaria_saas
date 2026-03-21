from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from datetime import datetime
from src.core.database import AsyncSessionLocal
from src.core.security import admin_required
from src.models.models import MedicalAttention, Patient, User, Organization, Ticket, TicketItem

router = APIRouter(prefix="/attentions", tags=["Attentions"], dependencies=[Depends(admin_required)])

async def get_org(username: str, session):
    res = await session.execute(
        select(User, Organization)
        .join(Organization, User.org_id == Organization.id)
        .where(User.username == username)
    )
    return res.first()

@router.post("/create")
async def create_attention(request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    patient_id = int(data.get("patient_id"))
    
    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        # Check plan
        if org.plan_type == 'lite':
            raise HTTPException(status_code=403, detail="El módulo de atenciones no está disponible en el plan Lite.")

        # Check for existing active attention for this patient
        active_att = await session.execute(
            select(MedicalAttention).where(
                MedicalAttention.patient_id == patient_id, 
                MedicalAttention.status.in_(['suspended', 'in_progress'])
            )
        )
        if active_att.scalar():
            raise HTTPException(status_code=400, detail="El paciente ya tiene una atención en curso o suspendida.")

        new_att = MedicalAttention(
            org_id=org.id,
            patient_id=patient_id,
            vet_id=user.id,
            status="in_progress",
            start_date=datetime.now()
        )
        session.add(new_att)
        await session.commit()
        return {"status": "success", "attention_id": new_att.id}

@router.get("/active")
async def get_active_attentions(username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        res = await session.execute(
            select(MedicalAttention, Patient)
            .join(Patient, MedicalAttention.patient_id == Patient.id)
            .options(selectinload(MedicalAttention.patient))
            .where(MedicalAttention.org_id == org.id, MedicalAttention.status != 'finished')
            .order_by(desc(MedicalAttention.start_date))
        )
        data = res.all()
        
        return [
            {
                "id": att.id,
                "patient_name": pat.name,
                "patient_id": pat.id,
                "start_date": att.start_date.strftime("%H:%M"),
                "status": att.status,
                "notes": att.notes
            } 
            for att, pat in data
        ]

@router.post("/update_status/{att_id}")
async def update_attention_status(att_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    new_status = data.get("status")
    notes = data.get("notes") # Optional notes update
    
    if new_status not in ['suspended', 'in_progress', 'finished']:
        raise HTTPException(status_code=400, detail="Estado inválido")

    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        res = await session.execute(select(MedicalAttention).where(MedicalAttention.id == att_id, MedicalAttention.org_id == org.id))
        att = res.scalar()
        if not att: raise HTTPException(status_code=404)
        
        if att.status == 'finished':
            raise HTTPException(status_code=400, detail="No se puede modificar una atención finalizada.")

        att.status = new_status
        if notes is not None:
             att.notes = notes
             
        await session.commit()
        return {"status": "success"}

@router.post("/finish/{att_id}")
async def finish_attention(att_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    items = data.get("items", []) # List of {description, price, quantity}
    payment_method = data.get("payment_method", "Efectivo")
    notes = data.get("notes")
    
    if not items:
        raise HTTPException(status_code=400, detail="Debe agregar al menos un servicio o producto.")

    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        res = await session.execute(select(MedicalAttention).where(MedicalAttention.id == att_id, MedicalAttention.org_id == org.id))
        att = res.scalar()
        if not att: raise HTTPException(status_code=404)
        
        if att.status == 'finished':
             raise HTTPException(status_code=400, detail="Atención ya finalizada.")

        # 1. Close Attention
        att.status = 'finished'
        att.end_date = datetime.now()
        if notes: att.notes = notes
        
        # 2. Generate Ticket
        # Get last ticket number
        last_ticket = await session.execute(
            select(Ticket).where(Ticket.org_id == org.id).order_by(desc(Ticket.id)).limit(1)
        )
        last_t = last_ticket.scalar()
        last_num = int(last_t.ticket_number) if last_t and last_t.ticket_number.isdigit() else 0
        new_num = f"{last_num + 1:06d}"
        
        total = sum(float(i['price']) * int(i.get('quantity', 1)) for i in items)
        
        ticket = Ticket(
            attention_id=att.id,
            org_id=org.id,
            ticket_number=new_num,
            total_amount=total,
            payment_status="paid", # Simplification: Assume paid on spot
            payment_method=payment_method
        )
        session.add(ticket)
        await session.flush() # Get Ticket ID
        
        # 3. Add Items
        for i in items:
            t_item = TicketItem(
                ticket_id=ticket.id,
                description=i['description'],
                unit_price=float(i['price']),
                quantity=int(i.get('quantity', 1)),
                subtotal=float(i['price']) * int(i.get('quantity', 1))
            )
            session.add(t_item)
            
        await session.commit()
        
        # 4. Pro: Generate PDF (Async task or immediate return?)
        
        return {"status": "success", "ticket_id": ticket.id}

@router.post("/finish_appointment/{app_id}")
async def finish_appointment_to_caja(app_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    items = data.get("items", [])
    payment_method = data.get("payment_method", "Efectivo")
    notes = data.get("notes")
    
    if not items:
        raise HTTPException(status_code=400, detail="Debe agregar al menos un servicio o producto.")

    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        # 1. Fetch Appointment to get patient
        from src.models.models import Appointment
        app_res = await session.execute(
            select(Appointment).where(Appointment.id == app_id, Appointment.org_id == org.id)
        )
        appointment = app_res.scalar()
        if not appointment:
            raise HTTPException(status_code=404, detail="Cita no encontrada.")
        
        # Try to find the Patient using the appointment's pet_name and owner
        # Appointment doesn't explicitly store patient_id, but uses pet_name and owner_id
        pat_res = await session.execute(
            select(Patient).where(
                Patient.org_id == org.id, 
                Patient.owner_id == appointment.owner_id, 
                Patient.name == appointment.pet_name
            )
        )
        patient = pat_res.scalar()
        if not patient:
            raise HTTPException(status_code=400, detail="El paciente de esta cita no está registrado en el sistema. Asegúrese de que el paciente exista.")

        # 2. Update Appointment Status
        appointment.status = 'attended'

        # 3. Create a Finished Attention directly
        att = MedicalAttention(
            org_id=org.id,
            patient_id=patient.id,
            vet_id=user.id,
            status="finished",
            start_date=appointment.date,
            end_date=datetime.now(),
            notes=notes or "Consulta generada directamente desde Citas."
        )
        session.add(att)
        await session.flush() # Get Attention ID

        # 4. Generate Ticket
        last_ticket = await session.execute(
            select(Ticket).where(Ticket.org_id == org.id).order_by(desc(Ticket.id)).limit(1)
        )
        last_t = last_ticket.scalar()
        last_num = int(last_t.ticket_number) if last_t and last_t.ticket_number.isdigit() else 0
        new_num = f"{last_num + 1:06d}"
        
        total = sum(float(i['price']) * int(i.get('quantity', 1)) for i in items)
        
        ticket = Ticket(
            attention_id=att.id,
            org_id=org.id,
            ticket_number=new_num,
            total_amount=total,
            payment_status="paid",
            payment_method=payment_method
        )
        session.add(ticket)
        await session.flush()
        
        # 5. Add Ticket Items
        for i in items:
            t_item = TicketItem(
                ticket_id=ticket.id,
                description=i['description'],
                unit_price=float(i['price']),
                quantity=int(i.get('quantity', 1)),
                subtotal=float(i['price']) * int(i.get('quantity', 1))
            )
            session.add(t_item)
            
        await session.commit()
        return {"status": "success", "ticket_id": ticket.id}
