
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
)

;


CREATE TABLE owners (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	phone_number VARCHAR, 
	name VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT _org_phone_uc UNIQUE (org_id, phone_number), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
)

;


CREATE TABLE services (
	id SERIAL NOT NULL, 
	org_id INTEGER, 
	name VARCHAR, 
	price FLOAT, 
	description TEXT, 
	category VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
)

;


CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR, 
	password_hash VARCHAR, 
	org_id INTEGER, 
	is_admin BOOLEAN, 
	is_superadmin BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(org_id) REFERENCES organizations (id)
)

;


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
)

;


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
)

;


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
)

;


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
)

;


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
)

;


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
)

;


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
)

;


CREATE TABLE ticket_items (
	id SERIAL NOT NULL, 
	ticket_id INTEGER, 
	description VARCHAR, 
	unit_price FLOAT, 
	quantity INTEGER, 
	subtotal FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id)
)

;

