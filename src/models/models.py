from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Text, UniqueConstraint, Index, JSON

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    slug = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    
    # SaaS Config per Org
    evolution_api_url = Column(String, nullable=True)
    evolution_api_key = Column(String, nullable=True)
    evolution_instance = Column(String, nullable=True)
    openai_api_key = Column(String, nullable=True)
    plan_type = Column(String, default="basic") # lite, basic, pro
    google_calendar_id = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users = relationship("User", back_populates="organization")
    services = relationship("Service", back_populates="organization")
    owners = relationship("Owner", back_populates="organization")
    patients = relationship("Patient", back_populates="organization")
    appointments = relationship("Appointment", back_populates="organization")
    clinical_records = relationship("ClinicalRecord", back_populates="organization")
    vaccinations = relationship("Vaccination", back_populates="organization")
    digital_certificates = relationship("DigitalCertificate", back_populates="organization")
    medical_attentions = relationship("MedicalAttention", back_populates="organization")
    tickets = relationship("Ticket", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    is_admin = Column(Boolean, default=False)
    is_superadmin = Column(Boolean, default=False)
    
    # Professional Profile
    full_name = Column(String, nullable=True) # Nombre Completo Profesional
    license_number = Column(String, nullable=True) # Matrícula / Registro
    signature_img = Column(String, nullable=True) # URL de imagen de firma
    stamp_img = Column(String, nullable=True) # URL de imagen de sello

    organization = relationship("Organization", back_populates="users")
    attentions = relationship("MedicalAttention", back_populates="vet")

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    name = Column(String, index=True)
    price = Column(Float)
    description = Column(Text, nullable=True)
    category = Column(String, index=True)

    organization = relationship("Organization", back_populates="services")

class Owner(Base):
    __tablename__ = "owners"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    phone_number = Column(String, index=True)
    name = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('org_id', 'phone_number', name='_org_phone_uc'),)

    organization = relationship("Organization", back_populates="owners")
    patients = relationship("Patient", back_populates="owner")
    appointments = relationship("Appointment", back_populates="owner")

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    name = Column(String, index=True)
    species = Column(String) 
    owner_id = Column(Integer, ForeignKey("owners.id"), index=True)
    medical_history_link = Column(String, nullable=True)
    breed = Column(String, nullable=True)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    sex = Column(String, nullable=True)
    
    __table_args__ = (UniqueConstraint('org_id', 'owner_id', 'name', name='_org_owner_pet_uc'),)

    organization = relationship("Organization", back_populates="patients")
    owner = relationship("Owner", back_populates="patients")
    vaccinations = relationship("Vaccination", back_populates="patient")
    clinical_records = relationship("ClinicalRecord", back_populates="patient")
    digital_certificates = relationship("DigitalCertificate", back_populates="patient")
    attentions = relationship("MedicalAttention", back_populates="patient")

class ClinicalRecord(Base):
    __tablename__ = "clinical_records"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text)
    vet_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="clinical_records")
    patient = relationship("Patient", back_populates="clinical_records")

class Vaccination(Base):
    __tablename__ = "vaccinations"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    vaccine_name = Column(String, index=True)
    date_administered = Column(DateTime(timezone=True), server_default=func.now())
    next_dose_date = Column(DateTime(timezone=True), nullable=True, index=True)
    
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    batch_number = Column(String, nullable=True)
    signature_hash = Column(String, nullable=True)
    signature_data = Column(Text, nullable=True)
    vet_stamp = Column(Text, nullable=True)

    organization = relationship("Organization", back_populates="vaccinations")
    patient = relationship("Patient", back_populates="vaccinations")

class DigitalCertificate(Base):
    __tablename__ = "digital_certificates"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    file_hash = Column(String, unique=True, index=True)
    storage_path = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, default=True)

    organization = relationship("Organization", back_populates="digital_certificates")
    patient = relationship("Patient", back_populates="digital_certificates")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    pet_name = Column(String, index=True)
    reason = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), index=True)
    date = Column(DateTime(timezone=True), index=True)
    status = Column(String, default="confirmed", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_apps_org_status', 'org_id', 'status'),
        Index('idx_apps_org_date', 'org_id', 'date'),
    )

    organization = relationship("Organization", back_populates="appointments")
    owner = relationship("Owner", back_populates="appointments")

class MedicalAttention(Base):
    __tablename__ = "medical_attentions"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), index=True)
    vet_id = Column(Integer, ForeignKey("users.id"), index=True)
    status = Column(String, default="in_progress")
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="medical_attentions")
    patient = relationship("Patient", back_populates="attentions")
    vet = relationship("User", back_populates="attentions")
    ticket = relationship("Ticket", back_populates="attention", uselist=False)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    attention_id = Column(Integer, ForeignKey("medical_attentions.id"), unique=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    ticket_number = Column(String, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    total_amount = Column(Float, default=0.0)
    currency = Column(String, default="ARS")
    payment_status = Column(String, default="pending")
    payment_method = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="tickets")
    attention = relationship("MedicalAttention", back_populates="ticket")
    items = relationship("TicketItem", back_populates="ticket")

class TicketItem(Base):
    __tablename__ = "ticket_items"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), index=True)
    description = Column(String)
    unit_price = Column(Float)
    quantity = Column(Integer, default=1)
    subtotal = Column(Float)
    ticket = relationship("Ticket", back_populates="items")

# Nuevas tablas requeridas para el sistema avanzado de certificados

class VeterinaryProfile(Base):
    __tablename__ = "perfiles_veterinarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String)
    matricula_profesional = Column(String)
    nombre_veterinaria = Column(String)
    firma_sello_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    certificados = relationship("VaccinationCertificate", back_populates="veterinario")

class VaccinationCertificate(Base):
    __tablename__ = "certificados_vacunacion"
    id = Column(Integer, primary_key=True, index=True)
    mascota_nombre = Column(String)
    mascota_especie = Column(String)
    dueno_nombre = Column(String)
    veterinario_id = Column(Integer, ForeignKey("perfiles_veterinarios.id"))
    vacunas_json = Column(JSON)
    pdf_url = Column(String)
    hash_control = Column(String)
    token_validacion = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    veterinario = relationship("VeterinaryProfile", back_populates="certificados")
    registros_integridad = relationship("CertificateIntegrityRecord", back_populates="certificado")

class CertificateIntegrityRecord(Base):
    __tablename__ = "registro_integridad_certificados"
    id = Column(Integer, primary_key=True, index=True)
    certificado_id = Column(Integer, ForeignKey("certificados_vacunacion.id"))
    hash_pdf = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    verificado = Column(Boolean, default=True)

    certificado = relationship("VaccinationCertificate", back_populates="registros_integridad")

