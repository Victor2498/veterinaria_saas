
import asyncio
from datetime import datetime, time, timedelta
from typing import List, Tuple
from sqlalchemy import select, and_
from src.core.database import AsyncSessionLocal
from src.models.models import Appointment

# Configuración básica de horarios (SaaS: esto podría estar en la DB por organización)
BUSINESS_HOURS = {
    0: (time(9, 0), time(18, 0)),  # Lunes
    1: (time(9, 0), time(18, 0)),  # Martes
    2: (time(9, 0), time(18, 0)),  # Miércoles
    3: (time(9, 0), time(18, 0)),  # Jueves
    4: (time(9, 0), time(18, 0)),  # Viernes
    5: (time(9, 0), time(13, 0)),  # Sábado
    6: None                        # Domingo (Cerrado)
}

SLOT_DURATION = timedelta(minutes=30)

async def get_available_slots(org_id: int, target_date: datetime.date) -> List[str]:
    """Retorna una lista de strings con los horarios disponibles (HH:MM) para una fecha."""
    day_of_week = target_date.weekday()
    hours = BUSINESS_HOURS.get(day_of_week)
    
    if not hours:
        return []

    start_time, end_time = hours
    
    # Obtener turnos ocupados para ese día y organización
    today_start = datetime.combine(target_date, time.min)
    today_end = datetime.combine(target_date, time.max)
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Appointment.date).where(
                and_(
                    Appointment.org_id == org_id,
                    Appointment.date >= today_start,
                    Appointment.date <= today_end,
                    Appointment.status == "confirmed"
                )
            )
        )
        occupied_slots = [dt.time().strftime("%H:%M") for dt in result.scalars()]

    available_slots = []
    current_dt = datetime.combine(target_date, start_time)
    end_dt = datetime.combine(target_date, end_time)

    # Si es hoy, solo mostrar horarios futuros
    now_arg = datetime.utcnow() - timedelta(hours=3)
    
    while current_dt + SLOT_DURATION <= end_dt:
        slot_str = current_dt.time().strftime("%H:%M")
        
        # Filtros: que no esté ocupado y que sea futuro si es hoy
        is_future = True
        if target_date == now_arg.date():
            is_future = current_dt > now_arg
            
        if slot_str not in occupied_slots and is_future:
            available_slots.append(slot_str)
            
        current_dt += SLOT_DURATION
        
    return available_slots

async def get_formatted_availability(org_id: int, days_ahead: int = 2) -> str:
    """Retorna un texto amigable con la disponibilidad de los próximos días."""
    now_arg = datetime.utcnow() - timedelta(hours=3)
    lines = []
    
    dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    for i in range(days_ahead + 1):
        target_date = (now_arg + timedelta(days=i)).date()
        slots = await get_available_slots(org_id, target_date)
        
        if slots:
            nombre = "Hoy" if i == 0 else ("Mañana" if i == 1 else dias_nombres[target_date.weekday()])
            # Mostrar solo los primeros 4 y últimos 2 slots si hay muchos para no saturar el prompt
            display_slots = slots if len(slots) <= 6 else slots[:4] + ["..."] + slots[-2:]
            lines.append(f"- {nombre} ({target_date.strftime('%d/%m')}): {', '.join(display_slots)}")
        elif i == 0 and not slots:
             continue # Si hoy ya cerró o no hay, no mostrar nada
        else:
            nombre = "Mañana" if i == 1 else dias_nombres[target_date.weekday()]
            lines.append(f"- {nombre}: Sin disponibilidad.")

    return "\n".join(lines) if lines else "No hay horarios disponibles próximamente."
