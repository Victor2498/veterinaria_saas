CREATE TABLE organizations (
	id SERIAL NOT NULL, 
	name VARCHAR, 
	slug VARCHAR, 
	is_active BOOLEAN, 
	evolution_api_url VARCHAR, 
	evolution_api_key VARCHAR, 
	evolution_instance VARCHAR, 
	openai_api_key VARCHAR, 
	plan_type VARCHAR, 
	google_calendar_id VARCHAR, 
	firma_png_url VARCHAR, 
	sello_png_url VARCHAR, 
	color_principal VARCHAR, 
	color_secundario VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_organizations_slug ON organizations (slug);

CREATE INDEX ix_organizations_id ON organizations (id);

CREATE UNIQUE INDEX ix_organizations_name ON organizations (name);

CREATE TABLE perfiles_veterinarios (
	id SERIAL NOT NULL, 
	nombre_completo VARCHAR, 
	matricula_profesional VARCHAR, 
	nombre_veterinaria VARCHAR, 
	firma_sello_url VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE INDEX ix_perfiles_veterinarios_id ON perfiles_veterinarios (id);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR, 
	password_hash VARCHAR, 
	org_id INTEGER, 
	is_admin BOOLEAN, 
	is_superadmin BOOLEAN, 
	full_name VARCHAR, 
	license_number VARCHAR, 
	signature_img VARCHAR, 
	stamp_img VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

CREATE INDEX ix_users_id ON users (id);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE services (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	name VARCHAR, 
	price FLOAT, 
	description TEXT, 
	category VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

CREATE INDEX ix_services_id ON services (id);

CREATE INDEX ix_services_org_id ON services (org_id);

CREATE INDEX ix_services_name ON services (name);

CREATE INDEX ix_services_category ON services (category);

CREATE TABLE owners (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	phone_number VARCHAR, 
	name VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT _org_phone_uc UNIQUE (org_id, phone_number), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

CREATE INDEX ix_owners_phone_number ON owners (phone_number);

CREATE INDEX ix_owners_org_id ON owners (org_id);

CREATE INDEX ix_owners_name ON owners (name);

CREATE INDEX ix_owners_id ON owners (id);

CREATE TABLE certificados_vacunacion (
	id SERIAL NOT NULL, 
	mascota_nombre VARCHAR, 
	mascota_especie VARCHAR, 
	dueno_nombre VARCHAR, 
	veterinario_id INTEGER, 
	vacunas_json JSON, 
	pdf_url VARCHAR, 
	hash_control VARCHAR, 
	token_validacion VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(veterinario_id) REFERENCES perfiles_veterinarios (id)
);

CREATE INDEX ix_certificados_vacunacion_id ON certificados_vacunacion (id);

CREATE UNIQUE INDEX ix_certificados_vacunacion_token_validacion ON certificados_vacunacion (token_validacion);

CREATE TABLE patients (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	name VARCHAR, 
	species VARCHAR, 
	owner_id INTEGER, 
	medical_history_link VARCHAR, 
	breed VARCHAR, 
	birth_date TIMESTAMP WITH TIME ZONE, 
	weight FLOAT, 
	height FLOAT, 
	sex VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT _org_owner_pet_uc UNIQUE (org_id, owner_id, name), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(owner_id) REFERENCES owners (id)
);

CREATE INDEX ix_patients_name ON patients (name);

CREATE INDEX ix_patients_owner_id ON patients (owner_id);

CREATE INDEX ix_patients_id ON patients (id);

CREATE INDEX ix_patients_org_id ON patients (org_id);

CREATE TABLE appointments (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	pet_name VARCHAR, 
	reason VARCHAR, 
	owner_id INTEGER, 
	date TIMESTAMP WITH TIME ZONE, 
	status VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(owner_id) REFERENCES owners (id)
);

CREATE INDEX idx_apps_org_date ON appointments (org_id, date);

CREATE INDEX ix_appointments_pet_name ON appointments (pet_name);

CREATE INDEX ix_appointments_status ON appointments (status);

CREATE INDEX ix_appointments_org_id ON appointments (org_id);

CREATE INDEX ix_appointments_date ON appointments (date);

CREATE INDEX ix_appointments_owner_id ON appointments (owner_id);

CREATE INDEX ix_appointments_id ON appointments (id);

CREATE INDEX idx_apps_org_status ON appointments (org_id, status);

CREATE TABLE registro_integridad_certificados (
	id SERIAL NOT NULL, 
	certificado_id INTEGER, 
	hash_pdf VARCHAR, 
	timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	verificado BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(certificado_id) REFERENCES certificados_vacunacion (id)
);

CREATE INDEX ix_registro_integridad_certificados_id ON registro_integridad_certificados (id);

CREATE TABLE clinical_records (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	patient_id INTEGER, 
	date TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	description TEXT, 
	vet_name VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id)
);

CREATE INDEX ix_clinical_records_patient_id ON clinical_records (patient_id);

CREATE INDEX ix_clinical_records_id ON clinical_records (id);

CREATE INDEX ix_clinical_records_org_id ON clinical_records (org_id);

CREATE TABLE vaccinations (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	patient_id INTEGER, 
	vaccine_name VARCHAR, 
	date_administered TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	next_dose_date TIMESTAMP WITH TIME ZONE, 
	is_signed BOOLEAN, 
	signed_at TIMESTAMP WITH TIME ZONE, 
	batch_number VARCHAR, 
	signature_hash VARCHAR, 
	signature_data TEXT, 
	vet_stamp TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id)
);

CREATE INDEX ix_vaccinations_id ON vaccinations (id);

CREATE INDEX ix_vaccinations_vaccine_name ON vaccinations (vaccine_name);

CREATE INDEX ix_vaccinations_patient_id ON vaccinations (patient_id);

CREATE INDEX ix_vaccinations_org_id ON vaccinations (org_id);

CREATE INDEX ix_vaccinations_next_dose_date ON vaccinations (next_dose_date);

CREATE TABLE digital_certificates (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	patient_id INTEGER, 
	file_hash VARCHAR, 
	storage_path VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	is_valid BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id)
);

CREATE INDEX ix_digital_certificates_org_id ON digital_certificates (org_id);

CREATE INDEX ix_digital_certificates_patient_id ON digital_certificates (patient_id);

CREATE UNIQUE INDEX ix_digital_certificates_file_hash ON digital_certificates (file_hash);

CREATE INDEX ix_digital_certificates_id ON digital_certificates (id);

CREATE TABLE medical_attentions (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	patient_id INTEGER, 
	vet_id INTEGER, 
	status VARCHAR, 
	start_date TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	end_date TIMESTAMP WITH TIME ZONE, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id), 
	FOREIGN KEY(vet_id) REFERENCES users (id)
);

CREATE INDEX ix_medical_attentions_id ON medical_attentions (id);

CREATE INDEX ix_medical_attentions_vet_id ON medical_attentions (vet_id);

CREATE INDEX ix_medical_attentions_org_id ON medical_attentions (org_id);

CREATE INDEX ix_medical_attentions_patient_id ON medical_attentions (patient_id);

CREATE TABLE tickets (
	id SERIAL NOT NULL, 
	attention_id INTEGER, 
	org_id INTEGER, 
	ticket_number VARCHAR, 
	date TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	total_amount FLOAT, 
	currency VARCHAR, 
	payment_status VARCHAR, 
	payment_method VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	UNIQUE (attention_id), 
	FOREIGN KEY(attention_id) REFERENCES medical_attentions (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

CREATE INDEX ix_tickets_org_id ON tickets (org_id);

CREATE INDEX ix_tickets_id ON tickets (id);

CREATE INDEX ix_tickets_ticket_number ON tickets (ticket_number);

CREATE TABLE ticket_items (
	id SERIAL NOT NULL, 
	ticket_id INTEGER, 
	description VARCHAR, 
	unit_price FLOAT, 
	quantity INTEGER, 
	subtotal FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
);

CREATE INDEX ix_ticket_items_ticket_id ON ticket_items (ticket_id);

CREATE INDEX ix_ticket_items_id ON ticket_items (id);

