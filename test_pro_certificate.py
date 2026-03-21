import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.services.certificate_pro import generate_pro_certificate

# Mock Data
mock_data = {
    "paciente": {
        "nombre": "Firulais",
        "id": "550e8400-e29b-41d4-a716-446655440000"
    },
    "vacunas": [
        {"fecha": "10/01/2026", "nombre": "Quíntuple", "lote": "V12345", "proxima": "10/01/2027"},
        {"fecha": "15/02/2026", "nombre": "Antirrábica", "lote": "R98765", "proxima": "15/02/2027"}
    ],
    "desparasitaciones": [
        {"fecha": "01/03/2026", "peso": "12.5kg", "tratamiento": "Total Full Comprimidos"},
        {"fecha": "05/03/2026", "peso": "12.6kg", "tratamiento": "Pipeta Frontline"}
    ],
    "profesional": {
        "nombre": "Dr. Juan Pérez",
        "matricula": "9988-V",
        "id": "vet_001"
    },
    "urls": {
        "firma": "C:/Users/victo/.gemini/antigravity/brain/414e4914-be8c-4d09-b03c-f82f973d6d8b/signature_sample_1773426130533.png",
        "sello": "C:/Users/victo/.gemini/antigravity/brain/414e4914-be8c-4d09-b03c-f82f973d6d8b/seal_sample_1773426425979.png",
        "validacion": "https://veterinaria-express.supabase.co/verify/550e8400"
    }
}

def test_generation():
    print("Iniciando generación de certificado de prueba...")
    try:
        pdf_bytes, cert_hash = generate_pro_certificate(mock_data)
        
        # Save to file
        output_path = "test_certificado_pro.pdf"
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
            
        print(f"✅ Certificado generado exitosamente: {output_path}")
        print(f"✅ Hash SHA-256: {cert_hash}")
        
    except Exception as e:
        print(f"❌ Error durante la generación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
