from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.security import admin_required
from src.core.database import AsyncSessionLocal
from src.models.models import User, Organization, Patient, Vaccination, DigitalCertificate, VaccinationCertificate, VeterinaryProfile, CertificateIntegrityRecord, Owner
from src.services.pdf_service import generate_vaccination_certificate
from src.services.generador_pdf import generar_certificado_vacunacion
from src.services.storage import storage_service
from sqlalchemy import select
from datetime import datetime
import hashlib
import uuid

router = APIRouter(prefix="/certificates", dependencies=[Depends(admin_required)])

@router.post("/generate_digital/{patient_id}")
async def generate_digital_certificate(patient_id: int, request: Request, username: str = Depends(admin_required)):
    """Genera, almacena y retorna un certificado Digital."""
    async with AsyncSessionLocal() as session:
        # 1. Auth & Plan Check
        res = await session.execute(
            select(User, Organization)
            .join(Organization, User.org_id == Organization.id)
            .where(User.username == username)
        )
        row = res.first()
        if not row: raise HTTPException(status_code=401)
        user, org = row

        if org.plan_type != "pro" and not user.is_superadmin:
            raise HTTPException(status_code=403, detail="Esta función es exclusiva del Plan Pro")

        # 2. Get Data
        pat_res = await session.execute(select(Patient).where(Patient.id == patient_id, Patient.org_id == org.id))
        patient = pat_res.scalar()
        if not patient: raise HTTPException(status_code=404)

        vac_res = await session.execute(
            select(Vaccination)
            .where(Vaccination.patient_id == patient_id)
            .order_by(Vaccination.date_administered.desc())
        )
        vaccinations = vac_res.scalars().all()

        # 3. Generate Metadata & Hash
        timestamp = datetime.now().isoformat()
        unique_str = f"{org.id}-{patient.id}-{timestamp}-{uuid.uuid4()}"
        cert_hash = hashlib.sha256(unique_str.encode()).hexdigest()[:16] # Short hash
        
        # Public Verification URL (Adjust base URL in production)
        # Assuming app runs on localhost or a domain. We need a way to know the base URL.
        # For now, using a placeholder or config.
        base_url = request.base_url
        verify_url = f"{base_url}verify/{cert_hash}"

        # 4. Sync VeterinaryProfile & Generate PDF
        vet_res = await session.execute(select(VeterinaryProfile).where(VeterinaryProfile.matricula_profesional == (user.license_number or 'M-000')))
        vet_profile = vet_res.scalar()
        
        current_name = user.full_name or user.username
        current_license = user.license_number or 'M-000'
        # Prioritize unified signature image from user profile with cache buster
        raw_signature = user.stamp_img or user.signature_img
        current_signature = f"{raw_signature}?t={uuid.uuid4().hex[:8]}" if raw_signature else None
        
        if not vet_profile:
            vet_profile = VeterinaryProfile(
                nombre_completo=current_name,
                matricula_profesional=current_license,
                nombre_veterinaria=org.name,
                firma_sello_url=current_signature
            )
            session.add(vet_profile)
            await session.flush()
        else:
            vet_profile.nombre_completo = current_name
            vet_profile.firma_sello_url = current_signature
            await session.flush()

        try:
            pdf_buffer = generate_vaccination_certificate(
                org_name=org.name,
                patient_name=patient.name,
                vaccinations=vaccinations,
                patient_weight=patient.weight,
                is_digital=True,
                cert_hash=cert_hash,
                verify_url=verify_url,
                signature_url=current_signature,
                vet_name=current_name,
                vet_license=current_license,
                firma_org_url=None, # Deprecated in favor of unified user signature
                sello_org_url=org.sello_png_url,
                org_colors={"primary": org.color_principal, "secondary": org.color_secundario}
            )
        except Exception as e:
            print(f"Error generating PDF: {e}")
            raise HTTPException(status_code=500, detail="Error generando el PDF")

        # 5. Store in Supabase
        file_path = f"certificates/{org.id}/{patient.id}/{cert_hash}.pdf"
        storage_res, error_msg = storage_service.upload_file(pdf_buffer.getvalue(), file_path)
        
        if not storage_res:
             raise HTTPException(status_code=503, detail=f"Error en almacenamiento: {error_msg}")

        # 6. Save Metadata to DB
        new_cert = DigitalCertificate(
            org_id=org.id,
            patient_id=patient.id,
            file_hash=cert_hash,
            storage_path=file_path,
            is_valid=True
        )
        session.add(new_cert)
        await session.commit()

        return {"status": "success", "message": "Certificado generado y almacenado", "cert_hash": cert_hash, "verify_url": verify_url}

@router.post("/emit_advanced/{vaccination_id}")
async def emit_advanced_certificate(vaccination_id: int, request: Request, username: str = Depends(admin_required)):
    """Emite un certificado de vacunación estricto para un registro usando fpdf2."""
    async with AsyncSessionLocal() as session:
        # Auth Config
        res = await session.execute(
            select(User, Organization)
            .join(Organization, User.org_id == Organization.id)
            .where(User.username == username)
        )
        row = res.first()
        if not row: raise HTTPException(status_code=401)
        user, org = row

        # Fetch Validation Data
        vac_res = await session.execute(
            select(Vaccination, Patient, Owner)
            .join(Patient, Vaccination.patient_id == Patient.id)
            .join(Owner, Patient.owner_id == Owner.id)
            .where(Vaccination.id == vaccination_id, Vaccination.org_id == org.id)
        )
        row_vac = vac_res.first()
        if not row_vac: raise HTTPException(status_code=404, detail="Registro de vacuna no encontrado")
        vaccination, patient, owner = row_vac
        
        # Verify or sync VeterinaryProfile
        vet_res = await session.execute(select(VeterinaryProfile).where(VeterinaryProfile.matricula_profesional == (user.license_number or 'M-000')))
        vet_profile = vet_res.scalar()
        
        # Latest data from user - Unified signature/sello
        current_name = user.full_name or user.username
        current_license = user.license_number or 'M-000'
        raw_signature = user.signature_img or user.stamp_img
        current_signature = f"{raw_signature}?t={uuid.uuid4().hex[:8]}" if raw_signature else None
        
        if not vet_profile:
            vet_profile = VeterinaryProfile(
                nombre_completo=current_name,
                matricula_profesional=current_license,
                nombre_veterinaria=org.name,
                firma_sello_url=current_signature
            )
            session.add(vet_profile)
            await session.flush()
        else:
            # Sync existing profile in case user updated their info
            vet_profile.nombre_completo = current_name
            vet_profile.firma_sello_url = current_signature
            await session.flush()

        # Build Document Token
        token_validacion = str(uuid.uuid4())
        base_url = str(request.base_url)
        
        # Build JSON Payload
        vacunas_json = [{
            "fecha": vaccination.date_administered.strftime("%Y-%m-%d") if vaccination.date_administered else "-",
            "nombre": vaccination.vaccine_name,
            "lote": vaccination.batch_number or "-",
            "proxima": vaccination.next_dose_date.strftime("%Y-%m-%d") if vaccination.next_dose_date else "-"
        }]

        nombre_due = owner.name if owner.name else (owner.phone_number or "Dueño/Tutor")

        try:
            pdf_bytes, file_hash = generar_certificado_vacunacion(
                nombre_veterinaria=org.name,
                mascota_nombre=patient.name,
                mascota_especie=patient.species or "Canino/Felino",
                dueno_nombre=nombre_due,
                veterinario_nombre=vet_profile.nombre_completo,
                veterinario_matricula=vet_profile.matricula_profesional,
                vacunas_json=vacunas_json,
                token_validacion=token_validacion,
                base_url=base_url,
                firma_sello_url=vet_profile.firma_sello_url
            )
        except Exception as e:
            print(f"Error generando PDF nuevo: {e}")
            raise HTTPException(status_code=500, detail="Error generando el certificado en PDF")

        file_path = f"certificados/{org.id}/{patient.id}/{file_hash}.pdf"
        storage_res, error_msg = storage_service.upload_file(pdf_bytes, file_path)
        
        # Wait, if `storage_res` returns false we should handle it (depends on the previous implementation)
        if not storage_res:
             raise HTTPException(status_code=503, detail=f"Error al subir: {error_msg}")

        public_pdf_url = storage_service.get_public_url(file_path)

        # Database strict saving
        new_cert = VaccinationCertificate(
            mascota_nombre=patient.name,
            mascota_especie=patient.species or "N/A",
            dueno_nombre=nombre_due,
            veterinario_id=vet_profile.id,
            vacunas_json=vacunas_json,
            pdf_url=public_pdf_url or file_path,
            hash_control=file_hash,
            token_validacion=token_validacion
        )
        session.add(new_cert)
        await session.flush()

        integrity_record = CertificateIntegrityRecord(
            certificado_id=new_cert.id,
            hash_pdf=file_hash,
            verificado=True
        )
        session.add(integrity_record)
        
        await session.commit()
        return {
            "status": "success", 
            "message": "Certificado avanzado generado.", 
            "token": token_validacion,
            "pdf_url": public_pdf_url,
            "hash": file_hash
        }

@router.get("/download/{cert_hash}")
async def download_certificate(cert_hash: str, username: str = Depends(admin_required)):
    """Descarga un certificado Digital almacenado."""
    async with AsyncSessionLocal() as session:
        # Check permissions (basic valid user check is enough, or strictly org check)
        # Ideally, we verify the user belongs to the org of the cert.
        pass # Optimization: implement fetch

        cert_res = await session.execute(select(DigitalCertificate).where(DigitalCertificate.file_hash == cert_hash))
        cert = cert_res.scalar()
        if not cert: raise HTTPException(status_code=404)

        # Get public URL or download content
        # If bucket is public, redirect. If private, download server-side and stream.
        # Let's assume public read for now or use signed url.
        
        url_res = storage_service.get_public_url(cert.storage_path)
        if url_res:
             # Redirect to Supabase URL directly
             from fastapi.responses import RedirectResponse
             return RedirectResponse(url_res)
        
        raise HTTPException(status_code=404, detail="Archivo no encontrado en almacenamiento")

@router.post("/send_whatsapp/{cert_hash}")
async def send_certificate_whatsapp(cert_hash: str, username: str = Depends(admin_required)):
    """Envía el certificado por WhatsApp al dueño."""
    from src.models.models import Owner
    from src.services.whatsapp import send_whatsapp_document

    async with AsyncSessionLocal() as session:
        # 1. Get Cert and related info
        stmt = (
            select(DigitalCertificate, Patient, Owner, Organization)
            .join(Patient, DigitalCertificate.patient_id == Patient.id)
            .join(Owner, Patient.owner_id == Owner.id)
            .join(Organization, DigitalCertificate.org_id == Organization.id)
            .where(DigitalCertificate.file_hash == cert_hash)
        )
        res = await session.execute(stmt)
        row = res.first()
        
        if not row: raise HTTPException(status_code=404, detail="Certificado no encontrado")
        cert, patient, owner, org = row

        # 2. Get Public URL
        # We need the public URL for WhatsApp to download and send it.
        # If storage is private, we'd need a signed URL or download+base64.
        # Assuming public bucket for 'certificates' based on earlier implementation.
        doc_url = storage_service.get_public_url(cert.storage_path)
        if not doc_url:
            raise HTTPException(status_code=404, detail="No se pudo obtener la URL del documento")

        # 3. Send WhatsApp
        if not owner.phone_number:
            raise HTTPException(status_code=400, detail="El dueño no tiene número de teléfono registrado")

        caption = f"Hola {owner.name or ''}, adjuntamos el Certificado de Vacunación Digital de {patient.name}. 🐾\nVerificable online."
        
        # Call service
        result = await send_whatsapp_document(
            phone=owner.phone_number,
            document_url=doc_url,
            caption=caption,
            api_url=org.evolution_api_url,
            api_key=org.evolution_api_key,
            instance_name=org.evolution_instance
        )

        if not result:
             raise HTTPException(status_code=502, detail="Error al enviar mensaje por WhatsApp")

        return {"status": "success", "message": "Enviado por WhatsApp correctamente"}
