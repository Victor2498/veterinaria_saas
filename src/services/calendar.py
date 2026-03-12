import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/calendar']
# Path to the service account file that the user must provide
SERVICE_ACCOUNT_FILE = 'src/core/service_account.json'

def get_calendar_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ Service account file not found at {SERVICE_ACCOUNT_FILE}")
        return None
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Error initializing calendar service: {e}")
        return None

async def create_calendar_event(pet_name: str, owner_name: str, date_time_str: str, calendar_id: str = None, duration_minutes: int = 30):
    """
    Crea un evento en el Google Calendar especificado.
    Si no se provee calendar_id, no se crea nada (en el SaaS esto es obligatorio configurar).
    """
    if not calendar_id:
        print("⚠️ No calendar_id provided for this organization. Skipping calendar event creation.")
        return

    service = get_calendar_service()
    if not service:
        return

    try:
        # Intentar parsear la fecha (maneja formatos con espacio o T)
        try:
            start_time = datetime.fromisoformat(date_time_str.replace(" ", "T"))
        except ValueError:
            # Fallback si el formato es distinto
            print(f"⚠️ Formato de fecha inválido: {date_time_str}")
            return

        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': f'Cita: {pet_name} ({owner_name})',
            'description': f'Cita médica para la mascota {pet_name}. Dueño: {owner_name}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
        }

        # Insertar en el calendario de la clínica (calendar_id suele ser su email)
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"✅ Evento creado en {calendar_id}: {event.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Error creating calendar event for {calendar_id}: {e}")
