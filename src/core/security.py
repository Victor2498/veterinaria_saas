import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Cookie, Depends, HTTPException, status
from src.core.database import AsyncSessionLocal
from src.models.models import User, Organization
from sqlalchemy import select

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dogbot-super-secret-must-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(admin_token: str = Cookie(None)):
    if not admin_token:
        return None
    try:
        payload = jwt.decode(admin_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

async def admin_required(username: str = Depends(get_current_user)):
    if not username:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail="Session expired",
            headers={"Location": "/login"}
        )
    return username

async def ui_access_required(username: str = Depends(admin_required)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User, Organization)
            .join(Organization, User.org_id == Organization.id)
            .where(User.username == username)
        )
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user, org = row
        if org.plan_type == "lite" and not user.is_superadmin:
             # Redirect to info page instead of error? Lite users SHOULD be able to see /subscription
             # but not the dashboard/patients/etc.
             return "lite_restricted" 
        return "full_access"
def check_plan_feature(current_plan: str, required_feature: str) -> bool:
    """Centralized logic to check if a plan has access to a feature."""
    hierarchy = ["lite", "basic", "pro", "premium"]
    
    # Normalizamos planes Pro y Premium como iguales
    plan_rank = {
        "lite": 0,
        "basic": 1,
        "pro": 2,
        "premium": 2 # Mismo nivel que Pro
    }
    
    # Definición de requerimientos mínimos
    feature_requirements = {
        "admin_dashboard": 1,        # Basic+
        "patient_management": 1,     # Basic+
        "export_vaccines": 1,        # Basic+
        "export_history": 2,         # Pro+
        "custom_bot_ai": 2           # Pro+
    }
    
    required_rank = feature_requirements.get(required_feature, 99)
    current_rank = plan_rank.get(current_plan.lower(), 0)
    
    return current_rank >= required_rank
