from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from src.core.database import AsyncSessionLocal
from src.models.models import PremiumCertificate, Patient, Organization, Vaccination, User
from sqlalchemy import select

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/verify/{cert_hash}", response_class=HTMLResponse)
async def verify_certificate(request: Request, cert_hash: str):
    """Endpoint público de verificación."""
    async with AsyncSessionLocal() as session:
        # 1. Buscar Certificado
        cert_res = await session.execute(
            select(PremiumCertificate).where(PremiumCertificate.file_hash == cert_hash)
        )
        cert = cert_res.scalar()
        
        if not cert:
            return templates.TemplateResponse("verify.html", {
                "request": request, 
                "valid": False, 
                "message": "Certificado no encontrado o inexistente."
            })
            
        if not cert.is_valid:
             return templates.TemplateResponse("verify.html", {
                "request": request, 
                "valid": False, 
                "message": "Este certificado ha sido revocado o anulado."
            })

        # 2. Obtener Datos Relacionados (Paciente, Org, Vacunas al momento de la foto? 
        # Idealmente el certificado es un snapshot. Pero mostraremos la data actual del paciente y las vacunas asociadas
        # Ojo: Si el certificado es un snapshot, deberíamos confiar en el PDF. 
        # Pero la verificación digital suele mostrar los datos vivos o los datos del snapshot guardados.
        # Por simplicidad, mostraremos los datos del paciente y el link al PDF.
        
        pat_res = await session.execute(
            select(Patient, Organization)
            .join(Organization, Patient.org_id == Organization.id)
            .where(Patient.id == cert.patient_id)
        )
        row = pat_res.first()
        if not row:
             return templates.TemplateResponse("verify.html", {"request": request, "valid": False, "message": "Datos de paciente no encontrados."})
        
        patient, org = row
        
        # Obtener vacunas (Todas? O solo las firmadas? Mostremos las vacunas del paciente para contexto)
        # O mejor, solo mostrar metadata del certificado.
        
        download_url = None
        from src.services.storage import storage_service
        try:
            download_url = storage_service.get_public_url(cert.storage_path)
        except:
            pass

        return templates.TemplateResponse("verify.html", {
            "request": request,
            "valid": True,
            "cert": cert,
            "patient": patient,
            "org": org,
            "download_url": download_url,
            "verification_date": datetime.now()
        })

from datetime import datetime
