from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from src.core.database import AsyncSessionLocal
from src.core.security import admin_required
from src.models.models import User, Organization, Appointment, Patient, Owner, Service
from sqlalchemy import select
from datetime import datetime
import io

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_required)])
templates = Jinja2Templates(directory="templates")

async def get_org(username: str, session):
    res = await session.execute(
        select(User, Organization)
        .join(Organization, User.org_id == Organization.id)
        .where(User.username == username)
    )
    return res.first()

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        if not row: raise HTTPException(status_code=404)
        user, org = row
        
        if org.plan_type == "lite" and not user.is_superadmin:
            return templates.TemplateResponse("lite_plan_info.html", {"request": request, "org": org, "username": username})

        # 1. Resumen Dashboard (Citas recientes)
        recent_res = await session.execute(
            select(Appointment, Owner)
            .join(Owner, Appointment.owner_id == Owner.id)
            .where(Appointment.org_id == org.id)
            .order_by(Appointment.date.desc())
            .limit(5)
        )
        
        # 2. Todas las Citas
        all_app_res = await session.execute(
            select(Appointment, Owner)
            .join(Owner, Appointment.owner_id == Owner.id)
            .where(Appointment.org_id == org.id)
            .order_by(Appointment.date.desc())
        )
        
        # 3. Todos los Pacientes
        pat_all_res = await session.execute(
            select(Patient, Owner)
            .join(Owner, Patient.owner_id == Owner.id)
            .where(Patient.org_id == org.id)
            .order_by(Patient.name)
        )
        
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "org": org,
            "username": username,
            "recent_appointments": recent_res.all(),
            "all_appointments": all_app_res.all(),
            "patients": pat_all_res.all(),
            "patients_count": len(pat_all_res.all()) # Simple count based on query length (not fully optimized but works for now)
        })

@router.get("/subscription", response_class=HTMLResponse)
async def subscription_page(request: Request, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        if not row: raise HTTPException(status_code=404)
        user, org = row
        
        plans = [
            {"name": "Lite", "id": "lite", "price": "15.000 ARS/mes", "features": ["WhatsApp", "Google Calendar"]},
            {"name": "Básico", "id": "basic", "price": "30.000 ARS/mes", "features": ["Todo lo Lite", "Panel Web"]},
            {"name": "Pro", "id": "pro", "price": "60.000 ARS/mes", "features": ["Todo lo Básico", "Audio", "IA Vision", "PDFs"]}
        ]

        return templates.TemplateResponse("subscription.html", {
            "request": request,
            "org": org,
            "plans": plans,
            "username": username
        })

from src.services.pdf_service import generate_clinical_history_pdf, generate_vaccination_certificate
from src.models.models import ClinicalRecord, Vaccination

@router.get("/export_history/{patient_id}")
async def export_history(patient_id: int, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        if not row: raise HTTPException(status_code=404)
        user, org = row
        
        if org.plan_type != "pro" and not user.is_superadmin:
            raise HTTPException(status_code=403, detail="Esta función requiere el plan PRO")

        # Fetch patient and records
        pat_res = await session.execute(select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id))
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404)
        
        rec_res = await session.execute(select(ClinicalRecord).where(ClinicalRecord.patient_id == patient_id).order_by(ClinicalRecord.created_at.desc()))
        records = rec_res.scalars().all()
        
        pdf_buffer = generate_clinical_history_pdf(org.name, "Cliente", patient.name, records)
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=historial_{patient.name}.pdf"})

@router.get("/export_vaccines/{patient_id}")
async def export_vaccines(patient_id: int, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        if not row: raise HTTPException(status_code=404)
        user, org = row
        
        if org.plan_type != "pro" and not user.is_superadmin:
            raise HTTPException(status_code=403, detail="Esta función requiere el plan PRO")

        pat_res = await session.execute(select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id))
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404)
        
        vac_res = await session.execute(select(Vaccination).where(Vaccination.patient_id == patient_id))
        vaccinations = vac_res.scalars().all()
        
        pdf_buffer = generate_vaccination_certificate(org.name, patient.name, vaccinations)
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=vacunas_{patient.name}.pdf"})

from src.services.billing import create_plan_payment_link

@router.post("/upgrade_plan/{plan_id}")
async def upgrade_plan_request(plan_id: str, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        if not row: raise HTTPException(status_code=404)
        user, org = row

        prices = {"pro": 60000, "basic": 30000, "lite": 15000}
        price = prices.get(plan_id, 30000)

        payment_url = await create_plan_payment_link(org.slug, plan_id, price)
        return {"status": "success", "payment_url": payment_url}

@router.post("/change_password")
async def change_password(request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Se requiere contraseña actual y nueva")
        
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar()
        if user:
            from src.core.security import get_password_hash, verify_password
            if not verify_password(old_password, user.password_hash):
                raise HTTPException(status_code=403, detail="Contraseña actual incorrecta")
                
            user.password_hash = get_password_hash(new_password)
            await session.commit()
            return {"status": "success"}
    return {"status": "error"}

@router.get("/export_history/{patient_id}")
async def export_history(patient_id: int, username: str = Depends(admin_required)):
    from fastapi.responses import StreamingResponse
    from src.services.pdf_service import generate_clinical_history_pdf
    from src.models.models import Patient, ClinicalRecord, Owner
    
    async with AsyncSessionLocal() as session:
        # 1. Get user/org for security context
        user_res = await session.execute(
            select(User, Organization).join(Organization, User.org_id == Organization.id).where(User.username == username)
        )
        u_row = user_res.first()
        if not u_row: raise HTTPException(status_code=401)
        user, org = u_row

        # 2. Get patient and ensure it belongs to this org
        pat_res = await session.execute(
            select(Patient, Owner).join(Owner, Patient.owner_id == Owner.id)
            .where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        p_row = pat_res.first()
        if not p_row: raise HTTPException(status_code=404, detail="Paciente no encontrado")
        patient, owner = p_row

        # 3. Get records
        rec_res = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.patient_id == patient_id).order_by(ClinicalRecord.created_at.desc())
        )
        records = rec_res.scalars().all()

        # 4. Generate PDF
        pdf_buffer = generate_clinical_history_pdf(org.name, owner.name, patient.name, records)
        
        filename = f"Historia_{patient.name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@router.get("/export_vaccines/{patient_id}")
async def export_vaccines(patient_id: int, username: str = Depends(admin_required)):
    from fastapi.responses import StreamingResponse
    from src.services.pdf_service import generate_vaccination_certificate
    from src.models.models import Patient, Vaccination
    
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(
            select(User, Organization).join(Organization, User.org_id == Organization.id).where(User.username == username)
        )
        u_row = user_res.first()
        if not u_row: raise HTTPException(status_code=401)
        user, org = u_row

        pat_res = await session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404, detail="Paciente no encontrado")

        vac_res = await session.execute(
            select(Vaccination).where(Vaccination.patient_id == patient_id).order_by(Vaccination.date_administered.desc())
        )
        vaccinations = vac_res.scalars().all()

        pdf_buffer = generate_vaccination_certificate(org.name, patient.name, vaccinations)
        
        filename = f"Vacunas_{patient.name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            pdf_buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
