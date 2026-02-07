import os
import asyncio
from typing import Dict, Any
from datetime import datetime
from src.services.whatsapp import send_whatsapp_message
from src.services.calendar import create_calendar_event
from src.core.database import AsyncSessionLocal
from src.models.models import Appointment, Owner, Patient, Vaccination, Organization
from sqlalchemy import select

def format_arg_date(date_str: str) -> str:
    """Convierte fecha a formato Argentino y día en Español (Ej: Lunes 10/02 15:00)"""
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    try:
        date_str = date_str.strip()
        dt = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(date_str, fmt)
                break
            except: continue
        
        if not dt:
            dt = datetime.fromisoformat(date_str.replace(" ", "T"))
        
        nombre_dia = dias[dt.weekday()]
        return f"{nombre_dia} {dt.strftime('%d/%m/%Y %H:%M')}"
    except:
        return date_str

async def save_db_record(data: Dict[str, Any], org: Organization):
    """Guarda el registro en PostgreSQL usando la configuración de la organización."""
    try:
        async with AsyncSessionLocal() as session:
            phone = data.get("phone", "")
            if not phone:
                 return

            # Buscar o crear el dueño por teléfono y organización
            result = await session.execute(
                select(Owner).where(Owner.phone_number == phone, Owner.org_id == org.id)
            )
            owner = result.scalars().first()

            if not owner:
                owner = Owner(phone_number=phone, name=data.get("owner_name"), org_id=org.id)
                session.add(owner)
                await session.flush()

            # Buscar o crear el paciente
            pet_name = data.get('pet_name', 'Mascota')
            patient_res = await session.execute(
                select(Patient).where(
                    Patient.owner_id == owner.id, 
                    Patient.name.ilike(pet_name),
                    Patient.org_id == org.id
                )
            )
            patient = patient_res.scalars().first()

            if not patient:
                patient = Patient(name=pet_name, owner_id=owner.id, species="Perro/Gato", org_id=org.id)
                session.add(patient)
                await session.flush()

            # Parsear fecha
            try:
                date_str = data.get('date_time', '')
                import re
                date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}-\d{2})[ T](\d{2}:\d{2})", date_str)
                if date_match:
                    found_date = date_match.group(1)
                    found_time = date_match.group(2)
                    if len(found_date) == 5: found_date = f"{datetime.now().year}-{found_date}"
                    dt_obj = datetime.fromisoformat(f"{found_date}T{found_time}")
                else:
                    dt_obj = datetime.fromisoformat(date_str.replace(" ", "T"))
            except:
                from datetime import timedelta
                dt_obj = datetime.utcnow() - timedelta(hours=3)

            appointment = Appointment(
                org_id=org.id,
                pet_name=pet_name,
                reason=data.get('reason', 'Consulta'),
                owner_id=owner.id,
                date=dt_obj,
                status="confirmed"
            )
            session.add(appointment)
            await session.commit()
    except Exception as e:
        print(f"[Booking] Error saving to DB: {e}")

async def notify_owner_whatsapp(data: Dict[str, Any], org: Organization):
    """Avisa al dueño vía WhatsApp usando la config de la clínica."""
    # En un SaaS real, el teléfono del dueño debería estar en la tabla Organization o User (Admin)
    # Por ahora seguimos usando el env o podemos agregar un campo org.admin_phone
    clinic_owner_phone = os.getenv("CLINIC_OWNER_PHONE")
    if not clinic_owner_phone: return
    
    formatted_date = format_arg_date(data.get('date_time', ''))
    
    message = (
        f"🚨 *NUEVO TURNO CONFIRMADO* 🚨\n"
        f"🏥 *Clínica:* {org.name}\n"
        f"🐶 *Paciente:* {data['pet_name']}\n"
        f"👤 *Dueño:* {data['owner_name']}\n"
        f"📅 *Fecha:* {formatted_date}\n"
    )

    await send_whatsapp_message(
        clinic_owner_phone, 
        message,
        api_url=org.evolution_api_url,
        api_key=org.evolution_api_key,
        instance_name=org.evolution_instance
    )

async def master_booking_flow(appointment_data: Dict[str, Any], org: Organization):
    """Coordina persistencia, calendario y notificaciones por organización."""
    await asyncio.gather(
        save_db_record(appointment_data, org),
        create_calendar_event(
            pet_name=appointment_data['pet_name'],
            owner_name=appointment_data['owner_name'],
            date_time_str=appointment_data['date_time'],
            calendar_id=getattr(org, "google_calendar_id", None)
        ),
        notify_owner_whatsapp(appointment_data, org)
    )

async def get_vaccination_history(phone: str, pet_name: str, org_id: int):
    try:
        async with AsyncSessionLocal() as session:
            owner_res = await session.execute(
                select(Owner).where(Owner.phone_number == phone, Owner.org_id == org_id)
            )
            owner = owner_res.scalars().first()
            if not owner: return []

            patient_res = await session.execute(
                select(Patient).where(
                    Patient.owner_id == owner.id, 
                    Patient.name.ilike(pet_name),
                    Patient.org_id == org_id
                )
            )
            patient = patient_res.scalars().first()
            if not patient: return []

            vac_res = await session.execute(
                select(Vaccination).where(
                    Vaccination.patient_id == patient.id,
                    Vaccination.org_id == org_id
                ).order_by(Vaccination.date_administered.desc())
            )
            return vac_res.scalars().all()
    except Exception as e:
        print(f"Error fetching vaccinations: {e}")
        return []
