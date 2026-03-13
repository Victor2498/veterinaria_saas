import io
import hashlib
import requests
from datetime import datetime
from fpdf import FPDF
import segno
from .image_processor import process_transparency

class CertificatePro(FPDF):
    def __init__(self, watermark_text="VETERINARIA EXPRESS"):
        # A4 Vertical (210 x 297 mm)
        super().__init__(orientation='P', unit='mm', format='A4')
        self.watermark_text = watermark_text
        # Set margins: Top 20, Bottom 20, Left 15, Right 15
        self.set_margins(left=15, top=20, right=15)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # Watermark: Diagonal, opacity 0.05
        self.set_font("Helvetica", "B", 50)
        self.set_text_color(184, 134, 11) # Gold base
        # Using a very light version or transparency if supported by fpdf2
        # fpdf2 supports alpha through set_alpha
        with self.local_context(fill_opacity=0.05):
            with self.rotation(45, 105, 148):
                self.set_xy(0, 148)
                self.cell(210, 0, self.watermark_text, align="C")
        
        # Identity Visual: Logo/Nombre centered
        if self.page_no() == 1:
            self.set_y(10)
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(0, 0, 0)
            self.cell(0, 10, "VETERINARIA EXPRESS", ln=True, align='C')
            
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(184, 134, 11) # Gold (#B8860B)
            self.cell(0, 10, "CERTIFICADO DIGITAL DE VACUNACIÓN", align='C')
            
            # Underline
            self.set_draw_color(184, 134, 11)
            self.line(15, 32, 195, 32)
            self.ln(12)

    def footer(self):
        # We handle the professional seal and QR in the main logic to control Y position
        # This footer is for page numbers if needed, or minimal info
        pass

def generate_pro_certificate(data):
    """
    Genera un PDF profesional basado en un objeto JSON.
    data: {
        "paciente": {"nombre": "...", "id": "..."},
        "vacunas": [{"fecha": "...", "nombre": "...", "lote": "...", "proxima": "..."}],
        "desparasitaciones": [{"fecha": "...", "peso": "...", "tratamiento": "..."}],
        "profesional": {"nombre": "...", "matricula": "...", "id": "..."},
        "urls": {"firma": "...", "sello": "...", "validacion": "..."}
    }
    """
    pdf = CertificatePro()
    pdf.add_page()
    
    # A. INFO PACIENTE
    paciente = data.get("paciente", {})
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(30, 8, "PACIENTE:", ln=False)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, paciente.get("nombre", "N/A").upper(), ln=True)
    
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"ID Certificado: {paciente.get('id', 'N/A')}", ln=True)
    pdf.ln(5)

    # B. TABLA: PLAN SANITARIO (VACUNAS)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "PLAN SANITARIO", ln=True)

    # Header Vacunas
    pdf.set_fill_color(184, 134, 11) # Gold (#B8860B)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    
    # Columnas: FECHA | VACUNA | LOTE | FIRMA VET. | PRÓX. VACUNA.
    col_widths = [25, 60, 30, 35, 30]
    headers = ["FECHA", "VACUNA", "LOTE", "FIRMA VET.", "PRÓX. VACUNA"]
    
    for i in range(len(headers)):
        pdf.cell(col_widths[i], 10, headers[i], border=0, fill=True, align='C')
    pdf.ln()

    # Data Vacunas
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 51, 51) # Dark Gray (#333333)
    
    # Cache firma y sello
    firma_url = data.get("urls", {}).get("firma")
    sello_url = data.get("urls", {}).get("sello")
    firma_bytes = None
    sello_bytes = None
    
    if firma_url:
        try:
            if firma_url.startswith(("http://", "https://")):
                resp = requests.get(firma_url, timeout=5)
                if resp.status_code == 200:
                    firma_bytes = io.BytesIO(resp.content)
            else:
                # Local path
                with open(firma_url, "rb") as f:
                    firma_bytes = io.BytesIO(f.read())
            
            # Apply transparency processing
            if firma_bytes:
                processed_bytes = process_transparency(firma_bytes.getvalue())
                firma_bytes = io.BytesIO(processed_bytes)
                
        except Exception as e:
            print(f"DEBUG: Error loading/processing firma: {e}")

    if sello_url:
        try:
            if sello_url.startswith(("http://", "https://")):
                resp = requests.get(sello_url, timeout=5)
                if resp.status_code == 200:
                    sello_bytes = io.BytesIO(resp.content)
            else:
                # Local path
                with open(sello_url, "rb") as f:
                    sello_bytes = io.BytesIO(f.read())
            
            # Apply transparency processing
            if sello_bytes:
                processed_bytes = process_transparency(sello_bytes.getvalue(), threshold=230)
                sello_bytes = io.BytesIO(processed_bytes)
                
        except Exception as e:
            print(f"DEBUG: Error loading/processing sello: {e}")

    fill = False
    vacunas = data.get("vacunas", [])
    for vac in vacunas:
        current_y = pdf.get_y()
        # Zebra stripes (#FFFDF9)
        pdf.set_fill_color(255, 253, 249) if fill else pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(col_widths[0], 12, vac.get("fecha", "-"), border='B', fill=True, align='C')
        pdf.cell(col_widths[1], 12, vac.get("nombre", "-"), border='B', fill=True, align='C')
        pdf.cell(col_widths[2], 12, vac.get("lote", "-"), border='B', fill=True, align='C')
        
        # Firma & Sello Cell
        pdf.cell(col_widths[3], 12, "", border='B', fill=True)
        # X position for signatures: 15 (margin) + 25 + 60 + 30 = 130
        
        with pdf.local_context(blend_mode='Multiply'):
            if sello_bytes:
                sello_bytes.seek(0)
                # Width increased to 32
                pdf.image(sello_bytes, x=130 + (col_widths[3]-32)/2, y=current_y + 0.5, w=32)
                
            if firma_bytes:
                # Stamp firma on top of seal
                # Width increased to 38
                firma_bytes.seek(0)
                pdf.image(firma_bytes, x=130 + (col_widths[3]-38)/2, y=current_y + 1, w=38)
            
        pdf.cell(col_widths[4], 12, vac.get("proxima", "-"), border='B', fill=True, align='C')
        pdf.ln()
        fill = not fill

    pdf.ln(10)

    # C. TABLA: DESPARASITACIÓN (Interna / Externa)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "DESPARASITACIÓN (Interna / Externa)", ln=True)

    # Header Desparasitación
    pdf.set_fill_color(210, 105, 30) # Burnt Orange (#D2691E)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    
    # Columnas: FECHA | PESO | TRATAMIENTO | FIRMA Y SELLO.
    desp_col_widths = [30, 30, 80, 40]
    desp_headers = ["FECHA", "PESO", "TRATAMIENTO", "FIRMA Y SELLO"]
    
    for i in range(len(desp_headers)):
        pdf.cell(desp_col_widths[i], 10, desp_headers[i], border=0, fill=True, align='C')
    pdf.ln()

    # Data Desparasitación
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 51, 51)
    
    fill = False
    desparasitaciones = data.get("desparasitaciones", [])
    for desp in desparasitaciones:
        current_y = pdf.get_y()
        pdf.set_fill_color(255, 253, 249) if fill else pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(desp_col_widths[0], 12, desp.get("fecha", "-"), border='B', fill=True, align='C')
        pdf.cell(desp_col_widths[1], 12, desp.get("peso", "-"), border='B', fill=True, align='C')
        pdf.cell(desp_col_widths[2], 12, desp.get("tratamiento", "-"), border='B', fill=True, align='C')
        
        # Firma & Sello Cell
        pdf.cell(desp_col_widths[3], 12, "", border='B', fill=True)
        # X position: 15 (margin) + 30 + 30 + 80 = 155
        
        with pdf.local_context(blend_mode='Multiply'):
            if sello_bytes:
                sello_bytes.seek(0)
                # Width increased to 40
                pdf.image(sello_bytes, x=155 + (desp_col_widths[3]-40)/2, y=current_y + 0.5, w=40)

            if firma_bytes:
                # Width increased to 50
                firma_bytes.seek(0)
                pdf.image(firma_bytes, x=155 + (desp_col_widths[3]-50)/2, y=current_y + 1, w=50)
            
        pdf.ln()
        fill = not fill

    # D. BLOQUE DE VALIDACIÓN FINAL (Centro - Solo QR)
    if pdf.get_y() > 240:
        pdf.add_page()
    
    qr_w = 40
    qr_x = (210 - qr_w) / 2
    qr_y = 235
    
    # Generar QR
    validacion_url = data.get("urls", {}).get("validacion", "https://supabase.com")
    qr = segno.make(validacion_url)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, kind='png', scale=5)
    
    pdf.image(qr_buffer, x=qr_x, y=qr_y, w=qr_w, h=qr_w)
    
    # ID de Validación centrado abajo del QR
    pdf.set_xy(15, qr_y + qr_w + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(180, 4, f"CÓDIGO DE VALIDACIÓN: {data.get('id', 'N/A')}", align='C', ln=True)
    pdf.ln(2)

    # SHA-256 Calculation
    pdf_bytes_array = pdf.output(dest='S')
    pdf_bytes = bytes(pdf_bytes_array)
    hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, hash_sha256
