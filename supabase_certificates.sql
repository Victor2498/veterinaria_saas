-- supabase_certificates.sql
-- Script de migracion para el sistema de certificados de vacunacion avanzado

CREATE TABLE IF NOT EXISTS perfiles_veterinarios (
    id SERIAL PRIMARY KEY,
    nombre_completo VARCHAR,
    matricula_profesional VARCHAR,
    nombre_veterinaria VARCHAR,
    firma_sello_url VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS certificados_vacunacion (
    id SERIAL PRIMARY KEY,
    mascota_nombre VARCHAR,
    mascota_especie VARCHAR,
    dueno_nombre VARCHAR,
    veterinario_id INTEGER REFERENCES perfiles_veterinarios(id),
    vacunas_json JSONB,
    pdf_url VARCHAR,
    hash_control VARCHAR,
    token_validacion VARCHAR UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS registro_integridad_certificados (
    id SERIAL PRIMARY KEY,
    certificado_id INTEGER REFERENCES certificados_vacunacion(id),
    hash_pdf VARCHAR,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verificado BOOLEAN DEFAULT TRUE
);

-- Note: Buckets creation typically requires interacting with the Supabase Storage API or the dashboard.
-- If this script is run via psql directly, bucket policies can be adjusted as follows:
-- (Assuming the 'storage' schema is available)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('firmas', 'firmas', false) ON CONFLICT DO NOTHING;
-- INSERT INTO storage.buckets (id, name, public) VALUES ('certificados', 'certificados', true) ON CONFLICT DO NOTHING;
