import io
import hashlib
from datetime import datetime
from fpdf import FPDF
import segno

class PDFCertificado(FPDF):
    def __init__(self, watermark_text="VETERINARIA SAAS"):
        super().__init__()
        self.watermark_text = watermark_text

    def header(self):
        # We handle watermark here
        self.set_font("Helvetica", "B", 50)
        self.set_text_color(240, 240, 240)  # Light grey
        # Save current state
        with self.local_context():
            with self.rotation(45, 10, 250):
                self.set_xy(10, 250)
                self.cell(0, 0, self.watermark_text, align="C")

def generar_certificado_vacunacion(
    nombre_veterinaria,
    mascota_nombre,
    mascota_especie,
    dueno_nombre,
    veterinario_nombre,
    veterinario_matricula,
    vacunas_json,
    token_validacion,
    base_url="https://ejemplo.com", # Needs to be updated or passed dynamically
    firma_sello_url=None
):
    """
    Generates a PDF certificate using fpdf2 and segno.
    Returns the PDF bytes and its SHA256 hash.
    """
    pdf = PDFCertificado(watermark_text=nombre_veterinaria.upper())
    pdf.add_page()

    # CABECERA
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(46, 80, 119) # Dark blue
    pdf.cell(0, 10, nombre_veterinaria.upper(), ln=True, align='C')
    
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "CERTIFICADO DIGITAL DE VACUNACIÓN", ln=True, align='C')
    
    pdf.line(10, pdf.get_y()+2, 200, pdf.get_y()+2)
    pdf.ln(10)

    # DATOS MASCOTA
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Datos del Paciente:", ln=True)
    pdf.set_font("Helvetica", "", 12)
    
    pdf.cell(50, 8, "Nombre:", ln=False)
    pdf.cell(0, 8, mascota_nombre, ln=True)
    
    pdf.cell(50, 8, "Especie:", ln=False)
    pdf.cell(0, 8, mascota_especie, ln=True)
    
    pdf.cell(50, 8, "Dueño/Tutor:", ln=False)
    pdf.cell(0, 8, dueno_nombre, ln=True)

    pdf.ln(10)

    # TABLA VACUNAS
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Historial de Vacunación Registrado:", ln=True)
    pdf.ln(2)

    # Headers
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(30, 8, "Fecha", border=1, fill=True, align='C')
    pdf.cell(70, 8, "Vacuna", border=1, fill=True, align='C')
    pdf.cell(40, 8, "Lote", border=1, fill=True, align='C')
    pdf.cell(50, 8, "Próxima Dosis", border=1, fill=True, align='C', ln=True)

    pdf.set_font("Helvetica", "", 10)
    for vac in vacunas_json:
        pdf.cell(30, 8, vac.get("fecha", "-"), border=1, align='C')
        pdf.cell(70, 8, vac.get("nombre", "-"), border=1, align='C')
        pdf.cell(40, 8, vac.get("lote", "-"), border=1, align='C')
        pdf.cell(50, 8, vac.get("proxima", "-"), border=1, align='C', ln=True)

    pdf.ln(15)

    # SECCION PROFESIONAL
    y_stamp = pdf.get_y()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Profesional Interviniente", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Dr/a. {veterinario_nombre}", ln=True)
    pdf.cell(0, 8, f"Matrícula: {veterinario_matricula}", ln=True)

    if firma_sello_url:
        # Nota: Idealmente firma_sello_url es un path local temporal o se descarga previamente 
        # para pasarlo aquí si es una URL HTTPS que FPDF no pueda leer directamente.
        # FPDF2 soporta URLs mediante urllib.
        try:
            # We place the stamp slightly to the right of the professional info
            pdf.image(firma_sello_url, x=130, y=y_stamp, w=40)
        except Exception as e:
            print(f"Error cargando el sello: {e}")

    # GENERACIÓN DE QR con segno
    # validation URL
    if not base_url.endswith("/"):
        base_url += "/"
    validacion_url = f"{base_url}validar/{token_validacion}"
    
    qr = segno.make(validacion_url)
    qr_buffer = io.BytesIO()
    # Save QR as png
    qr.save(qr_buffer, kind='png', scale=4)
    
    # We position the QR at the bottom right
    pdf.set_y(-50)
    pdf.image(qr_buffer, x=160, w=30)
    
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_xy(150, -18)
    pdf.cell(50, 4, "Escanee para validar autenticidad", align='C')
    
    # OUTPUT AND HASH
    pdf_bytes = pdf.output(dest='S')
    
    hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    return pdf_bytes, hash_sha256
