import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from src.services.generador_pdf import generar_certificado_vacunacion
import json

def test():
    try:
        pdf_bytes, file_hash = generar_certificado_vacunacion(
            nombre_veterinaria="Veterinaria García & Pérez",
            mascota_nombre="Gino Mó mascota",
            mascota_especie="Caninoé",
            dueno_nombre="Víctor Ramón",
            veterinario_nombre="Dra. María Belén",
            veterinario_matricula="MP 1234-Á",
            vacunas_json=[{
                "fecha": "2023-10-10",
                "nombre": "Rabia",
                "lote": "12345",
                "proxima": "2024-10-10"
            }],
            token_validacion="abcd-1234",
            base_url="http://localhost:8000",
            firma_sello_url=None
        )
        print(f"Success! Hash: {file_hash}")
        with open("test_out.pdf", "wb") as f:
            f.write(pdf_bytes)
        print("PDF saved to test_out.pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
