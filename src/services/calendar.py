import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Note: This requires interactive flow if no token. SaaS should use Service Accounts
            return None 

    return build('calendar', 'v3', credentials=creds)

async def create_calendar_event(pet_name: str, owner_name: str, date_time_str: str, duration_minutes: int = 30):
    service = get_calendar_service()
    if not service:
        print("❌ Calendar service not available.")
        return

    try:
        start_time = datetime.fromisoformat(date_time_str.replace(" ", "T"))
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': f'Cita: {pet_name} ({owner_name})',
            'description': f'Cita médica para la mascota {pet_name}. Dueño: {owner_name}',
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'America/Argentina/Buenos_Aires'},
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"✅ Evento creado: {event.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Error creating calendar event: {e}")
