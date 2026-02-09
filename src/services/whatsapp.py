import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

# Persistent session singleton
_session = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
    return _session

async def send_whatsapp_message(phone: str, text: str, api_url: str = None, api_key: str = None, instance_name: str = None):
    """
    Sends a text message using Evolution API with persistent session for speed.
    """
    url_base = (api_url or os.getenv("EVOLUTION_API_URL", "")).rstrip("/")
    key = api_key or os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN")
    instance = instance_name or os.getenv("INSTANCE_NAME", "DogBot")

    if not url_base or not key:
        print("❌ Error: Evolution API config missing.")
        return None

    clean_phone = "".join(filter(str.isdigit, phone))
    url = f"{url_base}/message/sendText/{instance}"
    headers = {"apikey": key, "Content-Type": "application/json"}
    
    payload = {
        "number": clean_phone,
        "text": text,
        "options": {"delay": 0, "presence": "composing", "linkPreview": False}
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status in [200, 201]:
                return await resp.json()
            else:
                error_text = await resp.text()
                print(f"❌ Error WhatsApp ({resp.status}): {error_text}")
                return None
    except Exception as e:
        print(f"❌ Critical error in WhatsApp service: {e}")
        return None

async def send_whatsapp_document(phone: str, document_url: str, caption: str = "", api_url: str = None, api_key: str = None, instance_name: str = None):
    """
    Sends a document/file (PDF, image, etc.) via Evolution API.
    """
    url_base = (api_url or os.getenv("EVOLUTION_API_URL", "")).rstrip("/")
    key = api_key or os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN")
    instance = instance_name or os.getenv("INSTANCE_NAME", "DogBot")

    if not url_base or not key:
        return None

    clean_phone = "".join(filter(str.isdigit, phone))
    # Evolution API v1.6+ endpoint structure for media
    url = f"{url_base}/message/sendMedia/{instance}"
    
    headers = {"apikey": key, "Content-Type": "application/json"}
    
    payload = {
        "number": clean_phone,
        "mediaMessage": {
            "mediatype": "document",
            "caption": caption,
            "media": document_url,
            "fileName": "Certificado_Vacunacion.pdf"
        },
        "options": {"delay": 1200, "presence": "composing", "linkPreview": False}
    }

    try:
        session = await get_session()
        async with session.post(url, json=payload, headers=headers) as resp:
            if resp.status in [200, 201]:
                return await resp.json()
            else:
                error_text = await resp.text()
                print(f"❌ Error sending doc ({resp.status}): {error_text}")
                return None
    except Exception as e:
        print(f"❌ Error in send_whatsapp_document: {e}")
        return None
