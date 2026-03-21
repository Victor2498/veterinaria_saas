from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.models import VaccinationCertificate, VeterinaryProfile, Patient, Organization, ClinicalRecord, Vaccination, Owner

router = APIRouter()

@router.get("/validar/{token_validacion}", response_class=HTMLResponse)
async def validar_certificado(token_validacion: str):
    async with AsyncSessionLocal() as session:
        # Buscar certificado por token
        cert_res = await session.execute(
            select(VaccinationCertificate, VeterinaryProfile)
            .join(VeterinaryProfile, VaccinationCertificate.veterinario_id == VeterinaryProfile.id)
            .where(VaccinationCertificate.token_validacion == token_validacion)
        )
        row = cert_res.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Certificado inválido")
            
        cert, vet = row
        
        # Valid HTML Build
        vacunas_html = ""
        # Handle safely if vacunas_json is a list
        vacunas_list = cert.vacunas_json if isinstance(cert.vacunas_json, list) else []
        for v in vacunas_list:
            fecha = v.get('fecha', '-')
            nombre = v.get('nombre', '-')
            lote = v.get('lote', '-')
            vacunas_html += f"<li>{fecha} - {nombre} (Lote: {lote})</li>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
                <title>Validación de Certificado</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; color: #333; }}
                    .container {{ max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; padding: 30px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
                    h1 {{ color: #28a745; text-align: center; font-size: 28px; border-bottom: 2px solid #28a745; padding-bottom: 10px; }}
                    h2 {{ color: #0056b3; font-size: 20px; margin-top: 25px; }}
                    ul {{ list-style-type: none; padding: 0; }}
                    li {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                    .footer {{ margin-top: 30px; text-align: center; color: #777; font-size: 14px; font-style: italic; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>CERTIFICADO AUTÉNTICO</h1>
                    
                    <h2>Datos del Documento:</h2>
                    <ul>
                        <li><strong>Mascota:</strong> {cert.mascota_nombre} ({cert.mascota_especie})</li>
                        <li><strong>Dueño:</strong> {cert.dueno_nombre}</li>
                        <li><strong>Veterinario:</strong> {vet.nombre_completo}</li>
                        <li><strong>Matrícula:</strong> {vet.matricula_profesional}</li>
                        <li><strong>Veterinaria:</strong> {vet.nombre_veterinaria}</li>
                        <li><strong>Hash del documento:</strong> {cert.hash_control}</li>
                    </ul>
                    
                    <h2>Historial Inmunológico:</h2>
                    <ul>
                        {vacunas_html}
                    </ul>
                    
                    <div class="footer">
                        <p>Documento inmutable generado criptográficamente.</p>
                        <p>Plataforma DogBot SaaS Universal 🐶</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

@router.get("/mascota/{patient_id}", response_class=HTMLResponse)
async def ver_pasaporte_mascota(patient_id: int):
    async with AsyncSessionLocal() as session:
        # Fetch Patient Data
        pat_res = await session.execute(
            select(Patient, Organization, Owner)
            .join(Organization, Patient.org_id == Organization.id)
            .join(Owner, Patient.owner_id == Owner.id)
            .where(Patient.id == patient_id)
        )
        row = pat_res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Paciente no encontrado")
            
        patient, org, owner = row
        
        # Fetch Vaccinations
        vac_res = await session.execute(
            select(Vaccination)
            .where(Vaccination.patient_id == patient_id)
            .order_by(Vaccination.date_administered.desc())
        )
        vaccinations = vac_res.scalars().all()
        
        # Fetch Clinical Records
        clin_res = await session.execute(
            select(ClinicalRecord)
            .where(ClinicalRecord.patient_id == patient_id)
            .order_by(ClinicalRecord.date.desc())
            .limit(10)
        )
        records = clin_res.scalars().all()
        
        vacs_html = "".join([f"<li>{v.date_administered.strftime('%Y-%m-%d') if v.date_administered else ''} - <strong>{v.vaccine_name}</strong> (Lote: {v.batch_number or '-'})</li>" for v in vaccinations])
        if not vacs_html: vacs_html = "<li>No hay vacunas registradas.</li>"
            
        recs_html = "".join([f"<li><strong>{r.date.strftime('%Y-%m-%d') if r.date else ''}</strong> - {r.description} ({r.vet_name})</li>" for r in records])
        if not recs_html: recs_html = "<li>No hay historial clínico.</li>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
                <title>Pasaporte Sanitario Digital - {patient.name}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; color: #333; background: #f9f9f9; }}
                    .container {{ max-width: 600px; margin: auto; background: white; border: 1px solid #ddd; border-radius: 12px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; border-bottom: 2px solid #0056b3; padding-bottom: 15px; margin-bottom: 20px; }}
                    h1 {{ color: #0056b3; margin: 0; font-size: 26px; }}
                    .org-name {{ color: #666; font-size: 16px; margin-top: 5px; }}
                    .phone {{ color: #0056b3; font-weight: bold; }}
                    h2 {{ color: #28a745; font-size: 18px; margin-top: 25px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                    .data-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }}
                    .data-item {{ background: #f1f8ff; padding: 10px; border-radius: 8px; font-size: 14px; border: 1px solid #e1e8f0; }}
                    ul {{ list-style-type: none; padding: 0; margin: 0; }}
                    li {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 14px; }}
                    li:nth-child(even) {{ background: #fafafa; }}
                    .footer {{ margin-top: 30px; text-align: center; color: #999; font-size: 12px; font-style: italic; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>PASAPORTE SANITARIO DIGITAL</h1>
                        <p class="org-name">Atendido en: <strong>{org.name}</strong></p>
                        <p class="org-name">Contacto: <span class="phone">{owner.phone_number or org.evolution_instance or 'No disponible'}</span></p>
                    </div>
                    
                    <div class="data-grid">
                        <div class="data-item"><strong>Nombre:</strong> {patient.name}</div>
                        <div class="data-item"><strong>Especie:</strong> {patient.species} {f'({patient.breed})' if patient.breed else ''}</div>
                        <div class="data-item"><strong>Dueño:</strong> {owner.name or '-'}</div>
                        <div class="data-item"><strong>Sexo:</strong> {patient.sex or '-'}</div>
                        <div class="data-item"><strong>Peso:</strong> {patient.weight or '-'} kg</div>
                        <div class="data-item"><strong>Nacimiento:</strong> {patient.birth_date.strftime('%Y-%m-%d') if patient.birth_date else '-'}</div>
                    </div>
                    
                    <h2>💉 Vacunas Vigentes / Historial</h2>
                    <ul>{vacs_html}</ul>
                    
                    <h2>📜 Últimos Registros Clínicos</h2>
                    <ul>{recs_html}</ul>
                    
                    <div class="footer">
                        <p>Documento digital verificado en línea.</p>
                        <p>Plataforma DogBot SaaS Universal 🐶</p>
                    </div>
                </div>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)
