from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from src.core.database import Base

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # SaaS Config per Org
    evolution_api_url = Column(String, nullable=True) # https://api.midominio.com
    evolution_api_key = Column(String, nullable=True) # API Key global de Evolution
    evolution_instance = Column(String, nullable=True) # Nombre de la instancia (ej: DogBot)
    openai_api_key = Column(String, nullable=True) # Opcional: llave propia por org
    plan_type = Column(String, default="basic") # basic, pro, premium
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    is_admin = Column(Boolean, default=False)
    is_superadmin = Column(Boolean, default=False)

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)

class Owner(Base):
    __tablename__ = "owners"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    phone_number = Column(String, index=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    name = Column(String, index=True)
    species = Column(String) 
    owner_id = Column(Integer, ForeignKey("owners.id"))
    medical_history_link = Column(String, nullable=True)
    breed = Column(String, nullable=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True) # Altura en cm
    sex = Column(String, nullable=True)

class ClinicalRecord(Base):
    __tablename__ = "clinical_records"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text)
    vet_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Vaccination(Base):
    __tablename__ = "vaccinations"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    vaccine_name = Column(String)
    date_administered = Column(DateTime(timezone=True), server_default=func.now())
    next_dose_date = Column(DateTime(timezone=True), nullable=True)

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    pet_name = Column(String)
    reason = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("owners.id"))
    date = Column(DateTime(timezone=True))
    status = Column(String, default="confirmed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
