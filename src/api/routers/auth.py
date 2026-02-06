from fastapi import APIRouter, Request, Response, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from src.core.database import AsyncSessionLocal
from src.core.security import verify_password, create_access_token, get_password_hash
from src.models.models import User, Organization
from sqlalchemy import select
import re

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_handle(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User, Organization)
            .join(Organization, User.org_id == Organization.id)
            .where(User.username == username)
        )
        row = res.first()
        
        if row:
            user, org = row
            if verify_password(password, user.password_hash):
                if not org.is_active:
                    return templates.TemplateResponse("login.html", {"request": request, "error": "Esta organización está desactivada."})
                
                # Create JWT Token
                access_token = create_access_token(data={"sub": username})
                target_url = "/superadmin" if user.is_superadmin else "/admin"
                response = RedirectResponse(url=target_url, status_code=303)
                response.set_cookie(key="admin_token", value=access_token, httponly=True)
                return response

    return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales inválidas"})

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("admin_token")
    return response

@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")
async def signup_handle(request: Request):
    form = await request.form()
    org_name = form.get("org_name")
    username = form.get("username")
    password = form.get("password")
    
    async with AsyncSessionLocal() as session:
        check_org = await session.execute(select(Organization).where(Organization.name == org_name))
        if check_org.scalar(): return templates.TemplateResponse("signup.html", {"request": request, "error": "La veterinaria ya existe."})
        
        check_user = await session.execute(select(User).where(User.username == username))
        if check_user.scalar(): return templates.TemplateResponse("signup.html", {"request": request, "error": "El usuario ya existe."})
        
        slug = re.sub(r'[^a-z0-9]', '-', org_name.lower().strip())
        new_org = Organization(name=org_name, slug=slug, plan_type="lite") # Default to Lite
        session.add(new_org)
        await session.flush()
        
        new_user = User(username=username, password_hash=get_password_hash(password), org_id=new_org.id, is_admin=True)
        session.add(new_user)
        await session.commit()
        
    return RedirectResponse(url="/login?registered=true", status_code=303)
