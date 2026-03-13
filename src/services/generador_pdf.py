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
        self.set_font("Helvetica", "B", 45)
        self.set_text_color(240, 240, 240)  # Very light grey
        with self.local_context():
            # Rotation center should be near the center of the page for centered watermark
            with self.rotation(45, 105, 148):
                self.set_xy(0, 148)
                self.cell(210, 0, self.watermark_text, align="C")

    def footer(self):
        # Footer with officiality notice
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Documento oficial generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - ID Único de Verificación", align='C')

def generar_certificado_vacunacion(
    nombre_veterinaria,
    mascota_nombre,
    mascota_especie,
    dueno_nombre,
    veterinario_nombre,
    veterinario_matricula,
    vacunas_json,
    token_validacion,
    base_url="https://ejemplo.com",
    firma_sello_url=None
):
    """
    Generates a professional PDF certificate using fpdf2 and segno.
    """
    pdf = PDFCertificado(watermark_text=nombre_veterinaria.upper())
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- HEADER BANNER ---
    pdf.set_fill_color(46, 80, 119)  # Dark Blue
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_y(12)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, nombre_veterinaria.upper(), ln=True, align='C')
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "SISTEMA INTEGRAL DE GESTIÓN VETERINARIA", ln=True, align='C')

    pdf.set_y(45)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(46, 80, 119)
    pdf.cell(0, 10, "CERTIFICADO OFICIAL DE VACUNACIÓN", ln=True, align='C')
    pdf.ln(5)

    # --- INFO BLOCKS ---
    y_start_info = pdf.get_y()
    
    # Block Style
    pdf.set_draw_color(230, 230, 230)
    pdf.set_fill_color(250, 250, 250)
    pdf.rect(10, y_start_info, 190, 35, 'FD')
    
    pdf.set_xy(15, y_start_info + 5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(40, 6, "DATOS DEL PACIENTE")
    pdf.set_xy(105, y_start_info + 5)
    pdf.cell(40, 6, "DATOS DEL TUTOR")
    
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)
    
    # Patient Data
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(20, 6, "Nombre: ", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(60, 6, mascota_nombre, ln=True)
    
    pdf.set_x(15)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(20, 6, "Especie: ", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(60, 6, mascota_especie, ln=True)
    
    # Owner Data (Positioned absolute to align with patient)
    pdf.set_xy(105, y_start_info + 13)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(20, 6, "Nombre: ", ln=False)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(60, 6, dueno_nombre, ln=True)

    pdf.set_xy(10, y_start_info + 45)

    # --- VACCINATION TABLE ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(46, 80, 119)
    pdf.cell(0, 8, "DETALLE DE INMUNIZACIONES APLICADAS", ln=True)
    pdf.ln(2)

    # Table Headers
    pdf.set_fill_color(46, 80, 119)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 10, " Fecha", border=0, fill=True, align='L')
    pdf.cell(75, 10, " Vacuna / Biológico", border=0, fill=True, align='L')
    pdf.cell(40, 10, " Lote No.", border=0, fill=True, align='L')
    pdf.cell(40, 10, " Próxima Dosis", border=0, fill=True, align='L', ln=True)

    # Table Body with Zebra Stripes
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    fill = False
    for vac in vacunas_json:
        pdf.set_fill_color(245, 247, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(35, 9, f" {vac.get('fecha', '-')}", border='B', fill=True, align='L')
        pdf.cell(75, 9, f" {vac.get('nombre', '-')}", border='B', fill=True, align='L')
        pdf.cell(40, 9, f" {vac.get('lote', '-')}", border='B', fill=True, align='L')
        pdf.cell(40, 9, f" {vac.get('proxima', '-')}", border='B', fill=True, align='L', ln=True)
        fill = not fill

    pdf.ln(10)

    # --- PROFESSIONAL SECTION & QR ---
    y_footer = pdf.get_y()
    
    # Ensure footer starts on a fresh page if we're too close to bottom
    if y_footer > 230:
        pdf.add_page()
        y_footer = pdf.get_y()
        
    # QR Code on the left
    if not base_url.endswith("/"):
        base_url += "/"
    validacion_url = f"{base_url}verify/{token_validacion}"
    
    qr = segno.make(validacion_url)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, kind='png', scale=4)
    
    # Base positioning for QR and Signature
    qr_x = 20
    sig_x = 120
    
    # Position QR
    pdf.image(qr_buffer, x=qr_x, y=y_footer, w=30)
    
    # Position Legend BELOW QR
    pdf.set_xy(qr_x - 5, y_footer + 32)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(40, 4, "VERIFICACIÓN ONLINE", ln=True, align='C')
    pdf.set_x(qr_x - 5)
    pdf.set_font("Helvetica", "", 6)
    pdf.multi_cell(40, 3, f"Escanee para verificar autenticidad.\n{validacion_url}", align='C')
    
    # Signature/Stamp on the right (parallel to QR)
    if firma_sello_url:
        try:
            pdf.image(firma_sello_url, x=sig_x + 10, y=y_footer - 5, w=50)
        except Exception as e:
            print(f"Error cargando el sello: {e}")
            
    pdf.set_xy(sig_x, y_footer + 32)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(70, 5, f"Dr/a. {veterinario_nombre}", ln=True, align='C')
    pdf.set_x(sig_x)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(70, 5, f"Matrícula: {veterinario_matricula}", ln=True, align='C')

    # Immuntability Hash at the very bottom
    pdf.set_y(-25)
    pdf.set_font("Courier", "", 7)
    pdf.set_text_color(180, 180, 180)
    pdf_bytes_array = pdf.output(dest='S')
    pdf_bytes = bytes(pdf_bytes_array)
    hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, hash_sha256
