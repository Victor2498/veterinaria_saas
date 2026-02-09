from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from src.core.database import AsyncSessionLocal
from src.models.models import Organization
from src.core.redis_client import redis_client
from sqlalchemy import select
import os
from src.services.webhook_processor import process_webhook_background

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
                print(f"DEBUG: Org not found or inactive: {org_slug}")
                # We return OK to avoid retries from WhatsApp if org is dead
                return {"status": "ignored", "reason": "org_not_found"}
            
            org_data = {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "evolution_api_url": org.evolution_api_url or os.getenv("EVOLUTION_API_URL"),
                "evolution_api_key": org.evolution_api_key or os.getenv("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_TOKEN"),
                "evolution_instance": org.evolution_instance or os.getenv("INSTANCE_NAME"),
                "openai_api_key": org.openai_api_key or os.getenv("OPENAI_API_KEY"),
                "google_calendar_id": org.google_calendar_id,
                "plan_type": org.plan_type or "pro"
            }
            await redis_client.set_org_config(org_slug, org_data)
    
    # 2. Security Check (Signature/API Key)
    incoming_key = request.headers.get("apikey")
    # Only enforce if org has a key configured
    if org_data.get("evolution_api_key") and incoming_key:
        if incoming_key != org_data["evolution_api_key"]:
            print(f"⚠️ Security Warning: Invalid API Key for {org_slug}")
            return {"status": "forbidden", "reason": "invalid_api_key"}
    
    # If no incoming key but org has one, technically we should block, 
    # but for migration safety we'll just log warning for now.
    if not incoming_key and org_data.get("evolution_api_key"):
        print(f"⚠️ Security Warning: Missing API Key header for {org_slug}")
    
    try:
        body = await request.json()
        print(f"DEBUG: Webhook received for {org_slug}. Offloading to background...")
        
        # Offload logic to Background Tasks ⚡
        background_tasks.add_task(process_webhook_background, body, org_data)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Webhook Dispatch Error: {e}")
        return {"status": "error"}
