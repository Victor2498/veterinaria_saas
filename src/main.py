from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.api.routers import auth, admin, webhooks, superadmin, certificates, verify, attentions, finance
import os

app = FastAPI(title="DogBot SaaS Universal")

# Templates and Static
templates = Jinja2Templates(directory="templates") # Keep legacy for now
app.mount("/static", StaticFiles(directory="templates/static"), name="static")

@app.on_event("startup")
async def startup():
    from src.core.init_db import init_db as initialize
    await initialize()

# Root
@app.get("/")
async def root():
    return {"status": "DogBot SaaS Online 🐶", "login": "/login"}

# Include Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(superadmin.router) # SaaS Owner Panel
app.include_router(webhooks.router)
app.include_router(certificates.router)
app.include_router(verify.router)
app.include_router(attentions.router)
app.include_router(finance.router)
