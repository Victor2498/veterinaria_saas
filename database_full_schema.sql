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
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
);

CREATE INDEX ix_organizations_name ON organizations (name);

CREATE INDEX ix_organizations_slug ON organizations (slug);

CREATE INDEX ix_organizations_id ON organizations (id);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR, 
	password_hash VARCHAR, 
	org_id INTEGER, 
	is_admin BOOLEAN, 
	is_superadmin BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
);

CREATE INDEX ix_users_username ON users (username);

CREATE INDEX ix_users_id ON users (id);

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

CREATE INDEX ix_services_org_id ON services (org_id);

CREATE INDEX ix_services_id ON services (id);

CREATE INDEX ix_services_category ON services (category);

CREATE INDEX ix_services_name ON services (name);

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

CREATE INDEX ix_owners_org_id ON owners (org_id);

CREATE INDEX ix_owners_phone_number ON owners (phone_number);

CREATE INDEX ix_owners_id ON owners (id);

CREATE INDEX ix_owners_name ON owners (name);

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

CREATE INDEX ix_patients_org_id ON patients (org_id);

CREATE INDEX ix_patients_id ON patients (id);

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

CREATE INDEX ix_clinical_records_org_id ON clinical_records (org_id);

CREATE INDEX ix_clinical_records_patient_id ON clinical_records (patient_id);

CREATE INDEX ix_clinical_records_id ON clinical_records (id);

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

CREATE INDEX ix_vaccinations_patient_id ON vaccinations (patient_id);

CREATE INDEX ix_vaccinations_org_id ON vaccinations (org_id);

CREATE INDEX ix_vaccinations_next_dose_date ON vaccinations (next_dose_date);

CREATE INDEX ix_vaccinations_id ON vaccinations (id);

CREATE INDEX ix_vaccinations_vaccine_name ON vaccinations (vaccine_name);

CREATE TABLE premium_certificates (
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

CREATE INDEX ix_premium_certificates_file_hash ON premium_certificates (file_hash);

CREATE INDEX ix_premium_certificates_patient_id ON premium_certificates (patient_id);

CREATE INDEX ix_premium_certificates_id ON premium_certificates (id);

CREATE INDEX ix_premium_certificates_org_id ON premium_certificates (org_id);

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

CREATE INDEX ix_appointments_id ON appointments (id);

CREATE INDEX ix_appointments_pet_name ON appointments (pet_name);

CREATE INDEX ix_appointments_status ON appointments (status);

CREATE INDEX idx_apps_org_status ON appointments (org_id, status);

CREATE INDEX ix_appointments_org_id ON appointments (org_id);

CREATE INDEX ix_appointments_date ON appointments (date);

CREATE INDEX ix_appointments_owner_id ON appointments (owner_id);

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

CREATE INDEX ix_medical_attentions_vet_id ON medical_attentions (vet_id);

CREATE INDEX ix_medical_attentions_org_id ON medical_attentions (org_id);

CREATE INDEX ix_medical_attentions_patient_id ON medical_attentions (patient_id);

CREATE INDEX ix_medical_attentions_id ON medical_attentions (id);

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

CREATE INDEX ix_tickets_ticket_number ON tickets (ticket_number);

CREATE INDEX ix_tickets_org_id ON tickets (org_id);

CREATE INDEX ix_tickets_id ON tickets (id);

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

CREATE INDEX ix_ticket_items_id ON ticket_items (id);

CREATE INDEX ix_ticket_items_ticket_id ON ticket_items (ticket_id);

