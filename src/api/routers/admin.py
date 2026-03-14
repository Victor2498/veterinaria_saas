from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from src.core.database import AsyncSessionLocal
from src.core.security import admin_required
from src.models.models import User, Organization, Appointment, Patient, Owner, Service
from sqlalchemy import select, func
from datetime import datetime
import io
import csv

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
        
        # 2. Todas las Citas (Optimized)
        # Count
        count_app_res = await session.execute(select(func.count()).select_from(Appointment).where(Appointment.org_id == org.id))
        total_appointments = count_app_res.scalar() or 0
        
        # List (Limit 50)
        all_app_res = await session.execute(
            select(Appointment, Owner)
            .join(Owner, Appointment.owner_id == Owner.id)
            .where(Appointment.org_id == org.id)
            .order_by(Appointment.date.desc())
            .limit(50)
        )
        
        # 3. Todos los Pacientes (Optimized)
        # Count
        count_pat_res = await session.execute(select(func.count()).select_from(Patient).where(Patient.org_id == org.id))
        total_patients = count_pat_res.scalar() or 0

        # List (Limit 50)
        pat_all_res = await session.execute(
            select(Patient, Owner)
            .join(Owner, Patient.owner_id == Owner.id)
            .where(Patient.org_id == org.id)
            .order_by(Patient.name)
            .limit(50)
        )

        # 4. Todos los Servicios
        services_res = await session.execute(
            select(Service)
            .where(Service.org_id == org.id)
            .order_by(Service.category, Service.name)
        )
        
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "org": org,
            "username": username,
            "user": user,
            "recent_appointments": recent_res.all(),
            "all_appointments": all_app_res.all(), # Contains only 50
            "total_appointments": total_appointments, # Real count
            "patients": pat_all_res.all(), # Contains only 50
            "patients_count": total_patients, # Real count
            "services": services_res.scalars().all()
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
        
        if org.plan_type not in ["pro"] and not user.is_superadmin:
            raise HTTPException(status_code=403, detail="Esta función requiere el plan PRO")

        pat_res = await session.execute(select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id))
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404)
        
        vac_res = await session.execute(select(Vaccination).where(Vaccination.patient_id == patient_id))
        vaccinations = vac_res.scalars().all()
        
        pdf_buffer = generate_vaccination_certificate(
            org.name, patient.name, vaccinations, patient.weight,
            firma_org_url=org.firma_png_url,
            sello_org_url=org.sello_png_url,
            org_colors={"primary": org.color_principal, "secondary": org.color_secundario}
        )
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


@router.post("/update_patient/{patient_id}")
async def update_patient(patient_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    
    async with AsyncSessionLocal() as session:
        # Get user/org for security
        user_res = await session.execute(
            select(User, Organization).join(Organization, User.org_id == Organization.id).where(User.username == username)
        )
        u_row = user_res.first()
        if not u_row: raise HTTPException(status_code=401)
        user, org = u_row

        # Get patient and ensure it belongs to this org
        pat_res = await session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404, detail="Paciente no encontrado")

        # Update fields
        patient.name = data.get("name")
        patient.species = data.get("species")
        patient.breed = data.get("breed")
        patient.weight = float(data.get("weight")) if data.get("weight") else None
        patient.height = float(data.get("height")) if data.get("height") else None
        patient.sex = data.get("sex")
        
        # Handle birth_date correctly
        bd_str = data.get("birth_date")
        if bd_str:
            try:
                patient.birth_date = datetime.strptime(bd_str, "%Y-%m-%d")
            except Exception as e:
                print(f"WARN: Error parsing birth_date: {e}")
        else:
            patient.birth_date = None

        await session.commit()
        return {"status": "success", "message": "Datos del paciente actualizados"}

@router.get("/patient_data/{patient_id}")
async def get_patient_detail_data(patient_id: int, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        # Get org
        row = await get_org(username, session)
        if not row: raise HTTPException(status_code=404)
        user, org = row

        # Get patient
        pat_res = await session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404)

        # Get records
        rec_res = await session.execute(
            select(ClinicalRecord).where(ClinicalRecord.patient_id == patient_id).order_by(ClinicalRecord.created_at.desc())
        )
        records = rec_res.scalars().all()

        # Get vaccinations
        vac_res = await session.execute(
            select(Vaccination).where(Vaccination.patient_id == patient_id).order_by(Vaccination.date_administered.desc())
        )
        vaccinations = vac_res.scalars().all()

        return {
            "patient": {
                "id": patient.id,
                "name": patient.name,
                "species": patient.species,
                "breed": patient.breed,
                "birth_date": patient.birth_date.strftime("%Y-%m-%d") if patient.birth_date else None,
                "weight": patient.weight,
                "height": patient.height,
                "sex": patient.sex
            },
            "records": [
                {"id": r.id, "date": r.created_at.strftime("%d/%m/%Y %H:%M"), "description": r.description, "vet_name": r.vet_name} 
                for r in records
            ],
            "vaccinations": [
                {
                    "id": v.id, 
                    "vaccine_name": v.vaccine_name, 
                    "date": v.date_administered.strftime("%d/%m/%Y"),
                    "next_dose": v.next_dose_date.strftime("%d/%m/%Y") if v.next_dose_date else "N/A",
                    "is_signed": v.is_signed,
                    "batch_number": v.batch_number
                } 
                for v in vaccinations
            ]
        }

@router.post("/add_clinical_record")
async def add_clinical_record(request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    patient_id = int(data.get("patient_id"))
    description = data.get("description")
    
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        # Verify ownership (Defensive casting and logging)
        print(f"DEBUG: add_clinical_record - patient_id value: {patient_id}, type: {type(patient_id)}")
        pat_res = await session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        if not pat_res.scalar(): raise HTTPException(status_code=403)
        
        new_rec = ClinicalRecord(
            org_id=org.id,
            patient_id=patient_id,
            description=description,
            vet_name=username
        )
        session.add(new_rec)
        await session.commit()
        return {"status": "success"}

@router.post("/add_vaccination")
async def add_vaccination(request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    patient_id = int(data.get("patient_id"))
    vaccine_name = data.get("vaccine_name")
    next_dose_date = data.get("next_dose_date")
    
    # Digital Docs Fields
    batch_number = data.get("batch_number")
    is_signed = data.get("is_signed", False)
    
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        # Verify ownership
        pat_res = await session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        if not pat_res.scalar(): raise HTTPException(status_code=403)
        
        # Validate Signature flag
        if is_signed:
            if org.plan_type != "pro" and not user.is_superadmin:
                raise HTTPException(status_code=403, detail="La firma digital requiere plan PRO")
            
            # Here we would normally validate Digital Signature/Stamp
            # For now, we trust the flag + auth
        
        next_dt = None
        if next_dose_date:
            try: 
                next_dt = datetime.strptime(next_dose_date, "%Y-%m-%d")
            except Exception as e: 
                print(f"WARN: Error parsing next_dose_date: {e}")

        new_vac = Vaccination(
            org_id=org.id,
            patient_id=patient_id,
            vaccine_name=vaccine_name,
            next_dose_date=next_dt,
            batch_number=batch_number,
            is_signed=is_signed,
            signed_at=datetime.now() if is_signed else None,
            signature_data=f"Firmado por: {user.full_name or user.username} - Mat: {user.license_number or '---'}" if is_signed else None,
            vet_stamp=f"{user.full_name}\nMat. {user.license_number}" if is_signed else None,
            signature_hash=user.signature_img or user.stamp_img if is_signed else None
        )
        session.add(new_vac)
        await session.commit()
        return {"status": "success"}

@router.post("/update_clinical_record/{record_id}")
async def update_clinical_record(record_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    description = data.get("description")
    
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        rec_res = await session.execute(select(ClinicalRecord).where(ClinicalRecord.id == record_id, ClinicalRecord.org_id == org.id))
        record = rec_res.scalar()
        if not record: raise HTTPException(status_code=404)
        
        record.description = description
        await session.commit()
        return {"status": "success"}

@router.post("/update_vaccination/{vac_id}")
async def update_vaccination(vac_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    vaccine_name = data.get("vaccine_name")
    next_dose_date = data.get("next_dose_date")
    
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        vac_res = await session.execute(select(Vaccination).where(Vaccination.id == vac_id, Vaccination.org_id == org.id))
        vaccination = vac_res.scalar()
        if not vaccination: raise HTTPException(status_code=404)
        
        vaccination.vaccine_name = vaccine_name
        if next_dose_date:
            try: 
                vaccination.next_dose_date = datetime.strptime(next_dose_date, "%Y-%m-%d")
            except Exception as e: 
                print(f"WARN: Error parsing next_dose_date update: {e}")
        else:
            vaccination.next_dose_date = None
            
        await session.commit()
        return {"status": "success"}
@router.post("/update_appointment_status/{appointment_id}")
async def update_appointment_status(appointment_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    new_status = data.get("status")
    
    if new_status not in ["confirmed", "attended", "waiting", "cancelled"]:
        raise HTTPException(status_code=400, detail="Estado inválido")
        
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        app_res = await session.execute(
            select(Appointment).where(Appointment.id == appointment_id, Appointment.org_id == org.id)
        )
        appointment = app_res.scalar()
        if not appointment: raise HTTPException(status_code=404)
        
        appointment.status = new_status
        await session.commit()
        return {"status": "success", "message": f"Estado de la cita actualizado a {new_status}"}

@router.delete("/delete_patient/{patient_id}")
async def delete_patient(patient_id: int, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        # Verify ownership and get patient
        pat_res = await session.execute(
            select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id)
        )
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404, detail="Paciente no encontrado")
        
        # Manually delete related records to ensure clean deletion (Cascading might be handled by DB, but being explicit is safer)
        from sqlalchemy import delete
        await session.execute(delete(ClinicalRecord).where(ClinicalRecord.patient_id == patient_id))
        await session.execute(delete(Vaccination).where(Vaccination.patient_id == patient_id))
        
        # Now delete the patient
        await session.delete(patient)
        await session.commit()
        
        return {"status": "success", "message": "Paciente y registros relacionados eliminados correctamente"}

@router.post("/add_service")
async def add_service(request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        new_service = Service(
            org_id=org.id,
            name=data.get("name"),
            price=float(data.get("price")),
            category=data.get("category", "General"),
            description=data.get("description")
        )
        session.add(new_service)
        await session.commit()
        return {"status": "success", "message": "Servicio creado"}

@router.post("/update_service/{service_id}")
async def update_service(service_id: int, request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        res = await session.execute(select(Service).where(Service.id == service_id, Service.org_id == org.id))
        service = res.scalar()
        if not service: raise HTTPException(status_code=404)
        
        service.name = data.get("name")
        service.price = float(data.get("price"))
        service.category = data.get("category")
        service.description = data.get("description")
        
        await session.commit()
        return {"status": "success"}

@router.delete("/delete_service/{service_id}")
async def delete_service(service_id: int, username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        res = await session.execute(select(Service).where(Service.id == service_id, Service.org_id == org.id))
        service = res.scalar()
        if not service: raise HTTPException(status_code=404)
        
        await session.delete(service)
        await session.commit()
        return {"status": "success"}
@router.get("/export_patients_csv")
async def export_patients_csv(username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        row = await get_org(username, session)
        user, org = row
        
        # Fetch patients with their owners
        res = await session.execute(
            select(Patient, Owner)
            .join(Owner, Patient.owner_id == Owner.id)
            .where(Patient.org_id == org.id)
            .order_by(Patient.name)
        )
        data = res.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Nombre Mascota", "Especie", "Raza", "Sexo", "Fecha Nacimiento", "Peso (kg)", "Altura (cm)", "Dueño", "Teléfono Dueño"])
        
        for p, o in data:
            writer.writerow([
                p.name,
                p.species,
                p.breed or "-",
                p.sex or "-",
                p.birth_date or "-",
                p.weight or "-",
                p.height or "-",
                o.name or "-",
                o.phone_number or "-"
            ])
            
        output.seek(0)
        
        headers = {
            'Content-Disposition': f'attachment; filename="backup_pacientes_{datetime.now().strftime("%Y%m%d")}.csv"'
        }
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers=headers
        )

from src.services.storage import storage_service
import uuid
import mimetypes

@router.post("/update_profile")
async def update_profile(
    full_name: str = Form(...),
    license_number: str = Form(None),
    signature: UploadFile = File(None),
    username: str = Depends(admin_required)
):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.username == username))
        user = user_res.scalar()
        if not user: raise HTTPException(status_code=404)
        
        user.full_name = full_name
        user.license_number = license_number
        
        if signature and signature.filename:
            file_bytes = await signature.read()
            ext = mimetypes.guess_extension(signature.content_type) or ".png"
            # Limit to images only
            if "image" not in signature.content_type:
                raise HTTPException(status_code=400, detail="Solo se permiten imágenes para la firma")
                
            path = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
            
            # Subir a supabase (asumiendo que storage_service soporta un bucket particular si modificas el init o se ajusta a "certificados")
            # Usaremos el bucket por defecto que tiene storage_service
            res, err = storage_service.upload_file(file_bytes, path, signature.content_type)
            if err:
                print(f"Error subiendo firma: {err}")
                raise HTTPException(status_code=500, detail="Error al subir la imagen de la firma")
                
            public_url = storage_service.get_public_url(path)
            if public_url:
                user.signature_img = public_url
                user.stamp_img = public_url # Guardamos en los dos campos por conveniencia
        
        await session.commit()
from src.services.image_processor import process_firma_sello

@router.post("/upload_firma")
async def upload_firma(
    firma_file: UploadFile = File(...),
    username: str = Depends(admin_required)
):
    print(f"DEBUG: upload_firma started for {username}")
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.username == username))
        user = user_res.scalar()
        if not user: raise HTTPException(status_code=404)
        
        # Format Check
        if firma_file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Formato no permitido. Use JPG, PNG o WEBP.")
            
        file_bytes = await firma_file.read()
        
        # Size Check
        if len(file_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="El archivo excede los 5MB permitidos.")
            
        try:
            # Pipiline: Resize, BG remove, optimize -> bytes
            processed_bytes = process_firma_sello(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error procesando la imagen: {e}")
            
        # Storage - Use user.id for signatures to avoid overwrites
        path = f"firmas/u_{user.id}/firma_{uuid.uuid4().hex[:8]}.png"
        from src.services.storage import storage_service
        res, err = storage_service.upload_file(processed_bytes, path, "image/png")
        if err:
            raise HTTPException(status_code=500, detail="Error al subir la imagen procesada")
            
        public_url = storage_service.get_public_url(path)
        
        # Update User Signature (instead of Org) - Consistent with Profile View
        user.signature_img = public_url
            
        await session.commit()
        return {"status": "success", "url": public_url}

@router.post("/upload_sello")
async def upload_sello(
    sello_file: UploadFile = File(...),
    username: str = Depends(admin_required)
):
    print(f"DEBUG: upload_sello started for {username}, file: {sello_file.filename}")
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.username == username))
        user = user_res.scalar()
        if not user: raise HTTPException(status_code=404)
        
        if sello_file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Formato no permitido. Use JPG, PNG o WEBP.")
            
        file_bytes = await sello_file.read()
        
        if len(file_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="El archivo excede los 5MB permitidos.")
            
        try:
            processed_bytes = process_firma_sello(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error procesando la imagen: {e}")
            
        # Storage - Use uuid for stamps to avoid cache issues
        path = f"sellos/{user.org_id}/sello_{uuid.uuid4().hex[:8]}.png"
        from src.services.storage import storage_service
        res, err = storage_service.upload_file(processed_bytes, path, "image/png")
        if err:
            raise HTTPException(status_code=500, detail="Error al subir la imagen procesada")
            
        public_url = storage_service.get_public_url(path)
        
        org_res = await session.execute(select(Organization).where(Organization.id == user.org_id))
        org = org_res.scalar()
        if org and public_url:
            org.sello_png_url = public_url
            
        await session.commit()
        return {"status": "success", "url": public_url}

@router.post("/update_colors")
async def update_colors(request: Request, username: str = Depends(admin_required)):
    data = await request.json()
    color_principal = data.get("color_principal")
    color_secundario = data.get("color_secundario")
    
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.username == username))
        user = user_res.scalar()
        if not user: raise HTTPException(status_code=404)
        
        org_res = await session.execute(select(Organization).where(Organization.id == user.org_id))
        org = org_res.scalar()
        if org:
            if color_principal:
                org.color_principal = color_principal
            if color_secundario:
                org.color_secundario = color_secundario
            await session.commit()
            return {"status": "success"}
        raise HTTPException(status_code=404)
