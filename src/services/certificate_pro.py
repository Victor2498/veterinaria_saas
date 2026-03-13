import io
import hashlib
import requests
from datetime import datetime
from fpdf import FPDF
import segno
from .image_processor import process_transparency, extract_signature_only

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
    
    # Cache firma
    firma_url = data.get("urls", {}).get("firma")
    # We'll keep two versions: the full processed image (for footer) and signature-only (for rows)
    firma_full_bytes = None
    firma_only_bytes = None
    
    if firma_url:
        try:
            temp_bytes = None
            if firma_url.startswith(("http://", "https://")):
                resp = requests.get(firma_url, timeout=5)
                if resp.status_code == 200:
                    temp_bytes = resp.content
            else:
                # Local path
                with open(firma_url, "rb") as f:
                    temp_bytes = f.read()
            
            if temp_bytes:
                # 1. Process transparency for the whole image
                transparent_bytes = process_transparency(temp_bytes)
                firma_full_bytes = io.BytesIO(transparent_bytes)
                
                # 2. Extract ONLY signature for the rows
                only_sig = extract_signature_only(transparent_bytes)
                firma_only_bytes = io.BytesIO(only_sig)
                
        except Exception as e:
            print(f"DEBUG: Error loading/processing firma: {e}")

    # Use firma_only_bytes for table rows
    firma_bytes = firma_only_bytes 

    fill = False
    vacunas = data.get("vacunas", [])
    for vac in vacunas:
        current_y = pdf.get_y()
        # Zebra stripes (#FFFDF9)
        pdf.set_fill_color(255, 253, 249) if fill else pdf.set_fill_color(255, 255, 255)
        
        pdf.cell(col_widths[0], 12, vac.get("fecha", "-"), border='B', fill=True, align='C')
        pdf.cell(col_widths[1], 12, vac.get("nombre", "-"), border='B', fill=True, align='C')
        pdf.cell(col_widths[2], 12, vac.get("lote", "-"), border='B', fill=True, align='C')
        
        # Firma Cell
        pdf.cell(col_widths[3], 12, "", border='B', fill=True)
        if firma_bytes:
            # Center firma in cell
            # X position is after first 3 columns: 15 + 25 + 60 + 30 = 130
            pdf.image(firma_bytes, x=130 + (col_widths[3]-20)/2, y=current_y + 2, w=20)
            
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
        
        # Firma Cell
        pdf.cell(desp_col_widths[3], 12, "", border='B', fill=True)
        if firma_bytes:
            # X position: 15 + 30 + 30 + 80 = 155
            pdf.image(firma_bytes, x=155 + (desp_col_widths[3]-20)/2, y=current_y + 2, w=20)
            
        pdf.ln()
        fill = not fill

    # D. BLOQUE DE VALIDACIÓN FINAL (Pie de Página)
    # The block needs about 45mm height. A4 is 297mm.
    # Bottom margin is 20mm. Max Y should be 277mm.
    # If we start at 230, we end at ~275.
    if pdf.get_y() > 225:
        pdf.add_page()
    
    pdf.set_y(232) # Position for the footer block
    
    # QR Code (Left)
    validacion_url = data.get("urls", {}).get("validacion", "https://supabase.com")
    qr = segno.make(validacion_url)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, kind='png', scale=5)
    
    qr_x = 15
    qr_y = pdf.get_y()
    pdf.image(qr_buffer, x=qr_x, y=qr_y, w=30, h=30)
    
    pdf.set_xy(qr_x, qr_y + 31)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(35, 4, "VERIFICACIÓN ONLINE", align='L')
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_x(qr_x)
    pdf.cell(35, 3, "Escanee para verificar autenticidad", align='L')

    # Sello Profesional (Right)
    # Using firma_full_bytes (which contains the user-provided composite image) 
    # as the official block next to QR
    sello_x = 150
    sello_y = qr_y - 2 
    sello_w = 40
    
    # Sello Profesional (Right)
    # Using firma_full_bytes (which contains the user-provided composite image) 
    # as the official block next to QR
    sello_x = 150
    sello_y = qr_y - 2 
    sello_w = 40
    
    if firma_full_bytes:
        try:
            firma_full_bytes.seek(0)
            pdf.image(firma_full_bytes, x=sello_x, y=sello_y, w=sello_w)
        except Exception as e:
            print(f"DEBUG: Error rendering firma_full: {e}")
    else:
        # Fallback to separate sello if provided
        temp_sello_url = data.get("urls", {}).get("sello")
        if temp_sello_url:
            try:
                s_bytes = None
                if temp_sello_url.startswith(("http://", "https://")):
                    resp = requests.get(temp_sello_url, timeout=5)
                    if resp.status_code == 200:
                        s_bytes = resp.content
                else:
                    with open(temp_sello_url, "rb") as f:
                        s_bytes = f.read()
                
                if s_bytes:
                    s_proc = process_transparency(s_bytes)
                    pdf.image(io.BytesIO(s_proc), x=sello_x, y=sello_y, w=sello_w)
            except Exception as e:
                print(f"DEBUG: Error fallback sello: {e}")
            
    # Professional Info text below seal
    profesional = data.get("profesional", {})
    pdf.set_xy(sello_x - 10, qr_y + 31)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(sello_w + 20, 5, profesional.get("nombre", "Veterinario Responsable"), align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(sello_x - 10)
    pdf.cell(sello_w + 20, 4, f"M.P. {profesional.get('matricula', 'N/D')}", align='C')

    # SHA-256 Calculation
    pdf_bytes_array = pdf.output(dest='S')
    pdf_bytes = bytes(pdf_bytes_array)
    hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, hash_sha256
