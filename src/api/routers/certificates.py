from fastapi import APIRouter, Depends, HTTPException, Request

from src.core.security import admin_required
from src.core.database import AsyncSessionLocal
from src.models.models import User, Organization, Patient, Vaccination, DigitalCertificate
from src.services.pdf_service import generate_vaccination_certificate
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

        # 4. Generate PDF
        try:
            pdf_buffer = generate_vaccination_certificate(
                org_name=org.name,
                patient_name=patient.name,
                vaccinations=vaccinations,
                patient_weight=patient.weight,
                is_digital=True,
                cert_hash=cert_hash,
                verify_url=verify_url
            )
        except Exception as e:
            print(f"Error generating PDF: {e}")
            raise HTTPException(status_code=500, detail="Error generando el PDF")

        # 5. Store in Supabase
        file_path = f"certificates/{org.id}/{patient.id}/{cert_hash}.pdf"
        storage_res = storage_service.upload_file(pdf_buffer.getvalue(), file_path)
        
        if not storage_res:
            # Fallback if storage fails? For now, raise error
             raise HTTPException(status_code=503, detail="Error almacenando el certificado en la nube")

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
