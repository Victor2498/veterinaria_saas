from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from src.core.database import AsyncSessionLocal
from src.models.models import Organization
from src.services.openai_service import get_chat_completion, transcribe_audio_file, get_vision_completion
from src.services.whatsapp import send_whatsapp_message
from src.services.booking import master_booking_flow, get_vaccination_history
from src.services.audio_logic import extract_audio_bytes, save_temp_audio
from src.services.media_logic import extract_media_base64
from sqlalchemy import select
import json
import re
from datetime import datetime
from src.core.redis_client import redis_client
from prompts import get_system_prompt

router = APIRouter()

@router.post("/webhook")
async def handle_default_webhook(request: Request, background_tasks: BackgroundTasks):
    return await handle_dynamic_webhook("central", request, background_tasks)

@router.post("/webhook/{org_slug}")
async def handle_dynamic_webhook(org_slug: str, request: Request, background_tasks: BackgroundTasks):
    # 1. Try Cache first
    org_data = await redis_client.get_org_config(org_slug)
    
    if not org_data:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Organization).where(Organization.slug == org_slug))
            org = res.scalar()
            
            if not org or not org.is_active:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            # Map model to dict for caching, using ENV as fallback if DB is empty
            org_data = {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "evolution_api_url": org.evolution_api_url or os.getenv("EVOLUTION_API_URL"),
                "evolution_api_key": org.evolution_api_key or os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN"),
                "evolution_instance": org.evolution_instance or os.getenv("INSTANCE_NAME"),
                "openai_api_key": org.openai_api_key or os.getenv("OPENAI_API_KEY"),
                "plan_type": org.plan_type or "pro" # Default to pro for testing if not set
            }
            await redis_client.set_org_config(org_slug, org_data)
    
    # Simple object-like access for compatibility with rest of code
    from argparse import Namespace
    org = Namespace(**org_data)

    print(f"DEBUG: Webhook hit for slug: {org_slug}")
    try:
        body = await request.json()
        event_type = body.get("event", "unknown")
        print(f"DEBUG: Event received: {event_type}")
        
        # Evolution v2 uses "data", v1/others might use top level
        data = body.get("data", body) if body.get("data") else body
        
        message_type = data.get("messageType")
        sender = data.get("pushName", "Usuario")
        
        # Handle different nested structures for phone
        key = data.get("key", {})
        phone = key.get("remoteJid", "").split("@")[0] if key.get("remoteJid") else ""
        if not phone and data.get("phone"): phone = data.get("phone") # Fallback
        
        print(f"DEBUG: Extracted -> Phone: {phone}, Sender: {sender}, Type: {message_type}")

        if not phone: 
            print(f"DEBUG: Ignored (no phone). Body keys: {list(body.keys())}")
            return {"status": "ignored"}

        user_input = ""
        image_base64 = None

        if message_type == "audioMessage":
            if org_data.get("plan_type") != "pro":
                await send_whatsapp_message(phone, "🐾 Tu plan actual no incluye mensajes de voz, pero puedes escribirme por texto y con gusto te ayudo. Contáctanos para subir a Pro.", 
                    api_url=org.evolution_api_url, api_key=org.evolution_api_key, instance_name=org.evolution_instance)
                return {"status": "plan_restricted"}
            try:
                audio_msg = data.get("message", {}).get("audioMessage", {})
                audio_bytes = await extract_audio_bytes(data, audio_msg)
                if audio_bytes:
                    temp_path = await save_temp_audio(audio_bytes, f"{phone}_{int(datetime.now().timestamp())}.ogg")
                    user_input = await transcribe_audio_file(temp_path, api_key=org.openai_api_key)
            except Exception as e:
                print(f"Audio error: {e}")
        elif message_type == "imageMessage":
            if org_data.get("plan_type") != "pro":
                 await send_whatsapp_message(phone, "🐾 Tu plan actual no incluye análisis de imágenes. Por favor, descríbeme lo que ves por texto o sube a Pro.", 
                    api_url=org.evolution_api_url, api_key=org.evolution_api_key, instance_name=org.evolution_instance)
                 return {"status": "plan_restricted"}
            try:
                image_msg = data.get("message", {}).get("imageMessage", {})
                image_base64 = await extract_media_base64(data, image_msg, "image", api_key=org.evolution_api_key)
                if image_base64:
                    # Usar un prompt que pida a la IA analizar la imagen en el contexto veterinario
                    vision_prompt = "Esta es una imagen enviada por un cliente a través de WhatsApp a una clínica veterinaria. Por favor, describe brevemente qué ves (heridas, síntomas visibles, tipo de mascota) para que pueda procesarlo."
                    user_input = await get_vision_completion(vision_prompt, image_base64, api_key=org.openai_api_key)
                    print(f"🖼 Análisis de imagen: {user_input}")
            except Exception as e:
                print(f"Image processing error: {e}")
        elif message_type == "conversation":
            user_input = data.get("message", {}).get("conversation", "")
        elif message_type == "extendedTextMessage":
            user_input = data.get("message", {}).get("extendedTextMessage", {}).get("text", "")

        if not user_input: 
            print("DEBUG: No user input found, ignoring.")
            return {"status": "ignored"}

        print(f"DEBUG: User input processed: {user_input}")

        # Memory Logic (Scoped by phone)
        history = await redis_client.get_history(phone)
        context = await redis_client.get_context(phone)
        pet_name = context.get("pet_name")
        
        vaccine_info = ""
        if pet_name:
            vacs = await get_vaccination_history(phone, pet_name, org.id)
            if vacs:
                vaccine_info = f"\nHISTORIAL DE VACUNAS para {pet_name}:\n"
                for v in vacs:
                    vaccine_info += f"- {v.vaccine_name}: {v.date_administered.strftime('%d/%m/%Y')}\n"

        system_msg = f"{get_system_prompt()}\n\nCONTEXTO: Clínica {org.name}.\nHoy es {datetime.now().strftime('%A, %d de %B de %Y')}.{vaccine_info}"
        
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        bot_response = await get_chat_completion(messages, api_key=org.openai_api_key)
        print(f"DEBUG: Bot response: {bot_response}")

        final_text = bot_response
        if "[[CONFIRMADO:" in bot_response:
            tag_match = re.search(r"\[\[CONFIRMADO:(.*?)\]\]", bot_response, re.DOTALL)
            if tag_match:
                booking_data = json.loads(tag_match.group(1).strip())
                booking_data.update({"owner_name": sender, "phone": phone})
                background_tasks.add_task(master_booking_flow, booking_data, org)
                final_text = re.sub(r"\[\[CONFIRMADO:.*?\]\]", "", bot_response, flags=re.DOTALL).strip()

        # Send response via WhatsApp with Org Config
        print(f"DEBUG: Sending WhatsApp message to {phone}...")
        send_result = await send_whatsapp_message(
            phone, final_text, 
            api_url=org.evolution_api_url, 
            api_key=org.evolution_api_key, 
            instance_name=org.evolution_instance
        )
        print(f"DEBUG: WhatsApp send result: {send_result}")

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": final_text})
        await redis_client.save_history(phone, history)

        return {"status": "ok"}

    except Exception as e:
        import traceback
        print(f"❌ Webhook error: {e}")
        traceback.print_exc()
        return {"status": "error"}
