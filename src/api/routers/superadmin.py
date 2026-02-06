from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.core.database import AsyncSessionLocal
from src.core.security import admin_required, get_password_hash
from src.models.models import User, Organization
from sqlalchemy import select
import re

router = APIRouter(prefix="/superadmin", dependencies=[Depends(admin_required)])
templates = Jinja2Templates(directory="templates")

async def superadmin_only(username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar()
        if not user or not user.is_superadmin:
            raise HTTPException(status_code=403, detail="Acceso denegado: Se requiere perfil SuperAdmin")
    return username

@router.post("/create_org")
async def create_org(request: Request, username: str = Depends(superadmin_only)):
    """Crea una nueva veterinaria y su usuario administrador inicial."""
    data = await request.json()
    name = data.get("name")
    # Generar slug básico si no viene
    slug = data.get("slug") or re.sub(r'[^a-z0-9]', '-', name.lower().strip())
    
    admin_user = data.get("admin_username")
    admin_pass = data.get("admin_password")

    async with AsyncSessionLocal() as session:
        # 1. Verificar si ya existe
        check = await session.execute(select(Organization).where(Organization.slug == slug))
        if check.scalar():
            return {"status": "error", "message": f"El slug '{slug}' ya existe."}

        # 2. Crear Org
        new_org = Organization(
            name=name,
            slug=slug,
            evolution_api_url=data.get("evolution_api_url"),
            evolution_api_key=data.get("evolution_api_key"),
            evolution_instance=data.get("evolution_instance"),
            openai_api_key=data.get("openai_api_key"),
            plan_type=data.get("plan_type", "basic")
        )
        session.add(new_org)
        await session.flush() # Para obtener el ID

        # 3. Crear Usuario Admin inicial para esa Org
        new_user = User(
            username=admin_user,
            password_hash=get_password_hash(admin_pass),
            org_id=new_org.id,
            is_superadmin=False
        )
        session.add(new_user)
        await session.commit()
    
    return {"status": "success", "org_id": new_org.id, "slug": slug}

@router.get("/", response_class=HTMLResponse)
async def superadmin_panel(request: Request, username: str = Depends(superadmin_only)):
    async with AsyncSessionLocal() as session:
        # Fetch all organizations
        orgs_res = await session.execute(select(Organization).order_by(Organization.id))
        orgs = orgs_res.scalars().all()
        
        return templates.TemplateResponse("superadmin.html", {
            "request": request, 
            "organizations": orgs,
            "username": username
        })

@router.post("/toggle_org/{org_id}")
async def toggle_org(org_id: int, username: str = Depends(superadmin_only)):
    """Activa o suspende una veterinaria (Corta su acceso al bot y panel)"""
    async with AsyncSessionLocal() as session:
        org_res = await session.execute(select(Organization).where(Organization.id == org_id))
        org = org_res.scalar()
        if org:
            org.is_active = not org.is_active
            await session.commit()
            # Opcional: Limpiar caché de Redis para que el cambio sea instantáneo en el bot
            from src.core.redis_client import redis_client
            await redis_client.redis.delete(f"org:config:{org.slug}")
            
    return {"status": "success", "new_state": org.is_active}

@router.get("/stats")
async def global_stats(username: str = Depends(superadmin_only)):
    """Resumen de métricas para el dueño del SaaS"""
    async with AsyncSessionLocal() as session:
        from src.models.models import Patient, Appointment
        total_orgs = await session.execute(select(Organization))
        total_patients = await session.execute(select(Patient))
        total_apps = await session.execute(select(Appointment))
        
        return {
            "total_clinics": len(total_orgs.scalars().all()),
            "total_patients_global": len(total_patients.scalars().all()),
            "total_appointments_global": len(total_apps.scalars().all())
        }
@router.post("/change_plan/{org_id}")
async def change_plan(org_id: int, request: Request, username: str = Depends(superadmin_only)):
    """Cambia el plan de una veterinaria (basic, pro, premium)"""
    data = await request.json()
    new_plan = data.get("plan")
    
    async with AsyncSessionLocal() as session:
        org_res = await session.execute(select(Organization).where(Organization.id == org_id))
        org = org_res.scalar()
        if org:
            org.plan_type = new_plan
            await session.commit()
            
            # Limpiar caché para que las restricciones de funciones se actualicen
            from src.core.redis_client import redis_client
            await redis_client.redis.delete(f"org:config:{org.slug}")
            
    return {"status": "success", "new_plan": new_plan}

@router.post("/change_password")
async def change_password(request: Request, username: str = Depends(superadmin_only)):
    data = await request.json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Se requiere contraseña actual y nueva")
        
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username == username))
        user = res.scalar()
        if user:
            from src.core.security import get_password_hash, verify_password
            if not verify_password(old_password, user.password_hash):
                raise HTTPException(status_code=403, detail="Contraseña actual incorrecta")
                
            user.password_hash = get_password_hash(new_password)
            await session.commit()
            return {"status": "success"}
    return {"status": "error"}
