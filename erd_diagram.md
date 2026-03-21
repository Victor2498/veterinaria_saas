# Diagrama de Base de Datos (ERD)

```mermaid
erDiagram
    organizations {
        INTEGER id PK
        VARCHAR name
        VARCHAR slug
        BOOLEAN is_active
        VARCHAR evolution_api_url
        VARCHAR evolution_api_key
        VARCHAR evolution_instance
        VARCHAR openai_api_key
        VARCHAR plan_type
        VARCHAR google_calendar_id
        DATETIME created_at
    }
    users {
        INTEGER id PK
        VARCHAR username
        VARCHAR password_hash
        INTEGER org_id FK
        BOOLEAN is_admin
        BOOLEAN is_superadmin
    }
    organizations ||--o{ users : ""
    services {
        INTEGER id PK
        INTEGER org_id FK
        VARCHAR name
        FLOAT price
        TEXT description
        VARCHAR category
    }
    organizations ||--o{ services : ""
    owners {
        INTEGER id PK
        INTEGER org_id FK
        VARCHAR phone_number
        VARCHAR name
        DATETIME created_at
    }
    organizations ||--o{ owners : ""
    patients {
        INTEGER id PK
        INTEGER org_id FK
        VARCHAR name
        VARCHAR species
        INTEGER owner_id FK
        VARCHAR medical_history_link
        VARCHAR breed
        DATETIME birth_date
        FLOAT weight
        FLOAT height
        VARCHAR sex
    }
    owners ||--o{ patients : ""
    organizations ||--o{ patients : ""
    clinical_records {
        INTEGER id PK
        INTEGER org_id FK
        INTEGER patient_id FK
        DATETIME date
        TEXT description
        VARCHAR vet_name
        DATETIME created_at
    }
    patients ||--o{ clinical_records : ""
    organizations ||--o{ clinical_records : ""
    vaccinations {
        INTEGER id PK
        INTEGER org_id FK
        INTEGER patient_id FK
        VARCHAR vaccine_name
        DATETIME date_administered
        DATETIME next_dose_date
        BOOLEAN is_signed
        DATETIME signed_at
        VARCHAR batch_number
        VARCHAR signature_hash
        TEXT signature_data
        TEXT vet_stamp
    }
    patients ||--o{ vaccinations : ""
    organizations ||--o{ vaccinations : ""
    premium_certificates {
        INTEGER id PK
        INTEGER org_id FK
        INTEGER patient_id FK
        VARCHAR file_hash
        VARCHAR storage_path
        DATETIME created_at
        BOOLEAN is_valid
    }
    patients ||--o{ premium_certificates : ""
    organizations ||--o{ premium_certificates : ""
    appointments {
        INTEGER id PK
        INTEGER org_id FK
        VARCHAR pet_name
        VARCHAR reason
        INTEGER owner_id FK
        DATETIME date
        VARCHAR status
        DATETIME created_at
    }
    organizations ||--o{ appointments : ""
    owners ||--o{ appointments : ""
    medical_attentions {
        INTEGER id PK
        INTEGER org_id FK
        INTEGER patient_id FK
        INTEGER vet_id FK
        VARCHAR status
        DATETIME start_date
        DATETIME end_date
        TEXT notes
        DATETIME created_at
    }
    patients ||--o{ medical_attentions : ""
    organizations ||--o{ medical_attentions : ""
    users ||--o{ medical_attentions : ""
    tickets {
        INTEGER id PK
        INTEGER attention_id FK
        INTEGER org_id FK
        VARCHAR ticket_number
        DATETIME date
        FLOAT total_amount
        VARCHAR currency
        VARCHAR payment_status
        VARCHAR payment_method
        DATETIME created_at
    }
    organizations ||--o{ tickets : ""
    medical_attentions ||--o{ tickets : ""
    ticket_items {
        INTEGER id PK
        INTEGER ticket_id FK
        VARCHAR description
        FLOAT unit_price
        INTEGER quantity
        FLOAT subtotal
    }
    tickets ||--o{ ticket_items : ""
```