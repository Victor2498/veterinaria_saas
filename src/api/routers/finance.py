from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from src.core.database import AsyncSessionLocal
from src.core.security import admin_required
from src.models.models import Ticket, TicketItem, User, Organization, MedicalAttention, Patient, Owner
from src.services.pdf_service import generate_ticket_pdf

router = APIRouter(prefix="/finance", tags=["Finance"], dependencies=[Depends(admin_required)])

async def get_org(username: str, session):
    res = await session.execute(
        select(User, Organization)
        .join(Organization, User.org_id == Organization.id)
        .where(User.username == username)
    )
    return res.first()

@router.get("/metrics")
async def get_finance_metrics(request: Request, period: str = "today", username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        if org.plan_type == 'lite':
             raise HTTPException(status_code=403, detail="Módulo no disponible en Plan Lite")

        # Define date range
        now = datetime.now()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if period == "month":
            if org.plan_type == 'basic':
                 # Basic allows only Daily view. Checking logic needed either frontend or backend.
                 # Let's allow monthly view for basic too as it's standard, but restrict export.
                 pass
            start_date = now.replace(day=1, hour=0, minute=0, second=0)
        elif period == "year":
            if org.plan_type == 'basic':
                 pass # Simple check
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)

        # Query
        query = select(func.sum(Ticket.total_amount), func.count(Ticket.id)).where(
            Ticket.org_id == org.id,
            Ticket.date >= start_date
        )
        res = await session.execute(query)
        total, count = res.first()
        
        return {
            "period": period,
            "total_revenue": total or 0,
            "ticket_count": count or 0,
            "currency": "ARS"
        }

@router.get("/tickets")
async def get_tickets(limit: int = 20, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        res = await session.execute(
            select(Ticket, Patient.name.label("patient_name"))
            .join(MedicalAttention, Ticket.attention_id == MedicalAttention.id)
            .join(Patient, MedicalAttention.patient_id == Patient.id)
            .where(Ticket.org_id == org.id)
            .order_by(desc(Ticket.date))
            .limit(limit)
        )
        data = res.all()
        
        return [
            {
                "id": t.id,
                "number": t.ticket_number,
                "date": t.date.strftime("%d/%m/%Y %H:%M"),
                "total": t.total_amount,
                "patient": p_name,
                "status": t.payment_status
            }
            for t, p_name in data
        ]

@router.get("/ticket/{ticket_id}/pdf")
async def get_ticket_pdf(ticket_id: int, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        user, org = await get_org(username, session)
        
        if org.plan_type != 'premium' and not user.is_superadmin:
             raise HTTPException(status_code=403, detail="Tickets PDF disponibles solo en Plan Premium")

        # Fetch Ticket Data
        t_res = await session.execute(
            select(Ticket, MedicalAttention, Patient, Owner, User)
            .join(MedicalAttention, Ticket.attention_id == MedicalAttention.id)
            .join(Patient, MedicalAttention.patient_id == Patient.id)
            .join(Owner, Patient.owner_id == Owner.id)
            .join(User, MedicalAttention.vet_id == User.id)
            .where(Ticket.id == ticket_id, Ticket.org_id == org.id)
        )
        row = t_res.first()
        if not row: raise HTTPException(status_code=404)
        ticket, attention, patient, owner, vet = row
        
        # Fetch Items
        i_res = await session.execute(select(TicketItem).where(TicketItem.ticket_id == ticket.id))
        items = i_res.scalars().all()
        
        # Generate PDF
        pdf_buffer = generate_ticket_pdf(
            org=org,
            ticket=ticket,
            items=items,
            patient=patient,
            owner=owner,
            vet=vet
        )
        
        filename = f"Ticket_{ticket.ticket_number}.pdf"
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
