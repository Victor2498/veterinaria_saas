import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "DogBot")

async def send_whatsapp_message(phone: str, text: str, api_url: str = None, api_key: str = None, instance_name: str = None):
    """
    Sends a text message using Evolution API with dynamic configuration.
    """
    # Fallback to env if not provided (legacy/default)
    url_base = (api_url or os.getenv("EVOLUTION_API_URL", "")).rstrip("/")
    key = api_key or os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN")
    instance = instance_name or os.getenv("INSTANCE_NAME", "DogBot")

    if not url_base or not key:
        print("❌ Error: Evolution API config missing.")
        return None

    clean_phone = "".join(filter(str.isdigit, phone))
    
    url = f"{url_base}/message/sendText/{instance}"
    headers = {
        "apikey": key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": clean_phone,
        "text": text,
        "options": {
            "delay": 1200,
            "presence": "composing",
            "linkPreview": False
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status in [200, 201]:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    print(f"❌ Error sending message: {resp.status} - {error_text}")
                    return None
    except Exception as e:
        print(f"❌ Critical error in WhatsApp service: {e}")
        return None
