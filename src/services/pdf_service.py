from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.units import inch
from datetime import datetime
import io
import qrcode
import requests
from src.services.image_processor import process_transparency


def _get_base_elements(org_name, title, is_digital=False):
    """Helper to create professional header for all PDFs."""
    styles = getSampleStyleSheet()
    elements = []
    
    # Header styled as a professional letterhead
    header_color = colors.HexColor("#2E5077") if not is_digital else colors.HexColor("#D4AF37") # Gold for digital
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=header_color,
        alignment=1, # Center
        spaceAfter=12
    )
    
    elements.append(Paragraph(org_name.upper(), header_style))
    elements.append(Paragraph(title, styles['Heading2']))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=4, spaceAfter=20))
    
    return elements, styles

def generate_clinical_history_pdf(org_name, owner_name, patient_name, records):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements, styles = _get_base_elements(org_name, "HISTORIAL CLÍNICO")

    # Patient info box
    info_data = [
        [Paragraph(f"<b>Propietario:</b> {owner_name}", styles['Normal']), 
         Paragraph(f"<b>Paciente:</b> {patient_name}", styles['Normal'])]
    ]
    info_table = Table(info_data, colWidths=[3*inch, 3*inch])
    elements.append(info_table)
    elements.append(Spacer(1, 24))

    # Records table
    data = [["FECHA", "DETALLES MÉDICOS"]]
    for r in records:
        data.append([r.created_at.strftime("%d/%m/%Y"), Paragraph(r.description, styles['Normal'])])

    t = Table(data, colWidths=[1*inch, 5.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4DA1A9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def draw_watermark(canvas, doc, watermark_text):
    """Draws a centered diagonal watermark."""
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 50)
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setFillColor(colors.lightgrey, alpha=0.15)
    
    # Position in center of page
    canvas.translate(4.25 * inch, 5.5 * inch)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, watermark_text.upper())
    canvas.restoreState()

def generate_vaccination_certificate(org_name, patient_name, vaccinations, patient_weight=None, is_digital=False, cert_hash=None, verify_url=None, signature_url=None, vet_name=None, vet_license=None, firma_org_url=None, sello_org_url=None, org_colors=None):
    """Certificado oficial de vacunación con formato de libreta sanitaria (Básico y Digital)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    org_colors = org_colors or {}
    primary_color = org_colors.get("primary") or ("#D4AF37" if is_digital else "#E38E49")
    secondary_color = org_colors.get("secondary") or ("#FFF8DC" if is_digital else "#F9D5B1")

    # Layout Pre-Calculation
    qr_img = None
    if is_digital and verify_url:
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(verify_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_img = Image(qr_buffer, width=1.1*inch, height=1.1*inch)

    title_text = "CERTIFICADO DIGITAL DE VACUNACIÓN" if is_digital else "LIBRETA SANITARIA"
    elements, styles = _get_base_elements(org_name, title_text, is_digital)

    if is_digital:
        # Re-arrange header into a table for the digital version
        elements.pop() # Remove HR
        elements.pop() # Remove Title
        elements.pop() # Remove Org Name
        
        header_color = colors.HexColor(primary_color)
        title_style = ParagraphStyle('CertTitle', parent=styles['Heading1'], fontSize=16, textColor=header_color, alignment=1)
        patient_style = ParagraphStyle('PatientStyle', parent=styles['Normal'], fontSize=10, leading=12)
        badge_style = ParagraphStyle('DigitalBadge', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=1)

        patient_info = [
            Paragraph(f"<b>PACIENTE:</b><br/>{patient_name.upper()}", patient_style),
            Paragraph(f"<font size=8 color=grey>ID: {cert_hash}</font>", patient_style) if cert_hash else ""
        ]
        
        qr_col = []
        if qr_img:
            # Removed legend per user request, keeping only the QR
            qr_col.append(qr_img)
        
        # 3-Column Header Table
        # Widths: Patient (2.0) | Title (2.5) | QR (2.0) -> More separation and right-alignment
        h_data = [[patient_info, Paragraph(title_text, title_style), qr_col]]
        h_table = Table(h_data, colWidths=[2.1*inch, 2.5*inch, 1.9*inch])
        h_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('VALIGN', (2,0), (2,0), 'BOTTOM'), # Align QR base to bottom
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'CENTER'),
            ('ALIGN', (2,0), (2,0), 'RIGHT'), # Push QR to right margin
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (1,0), 10),
            ('BOTTOMPADDING', (2,0), (2,0), 0), # QR touches the line
        ]))
        
        elements.append(Paragraph(f"<b>{org_name.upper()}</b>", ParagraphStyle('OrgName', parent=styles['Normal'], fontSize=9, textColor=colors.grey, spaceAfter=8)))
        elements.append(h_table)
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=2, spaceAfter=20))
    else:
        elements.append(Paragraph(f"<b>PACIENTE:</b> {patient_name.upper()}", styles['Normal']))
        elements.append(Spacer(1, 15))

    # Local image cache for performance (especially for multi-vet certificates)
    _image_cache = {}

    def fetch_image(url, width, height):
        if not url: return None
        if url in _image_cache:
            return Image(io.BytesIO(_image_cache[url]), width=width, height=height)
        
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # Apply transparency processing
                proc_bytes = process_transparency(resp.content)
                _image_cache[url] = proc_bytes
                return Image(io.BytesIO(proc_bytes), width=width, height=height)
        except Exception as e:
            print(f"Error fetching image {url}: {e}")
        return None

    # Global signature (fallback)
    global_sig_img = fetch_image(signature_url, 90, 40)
    global_sig_stamp_img = fetch_image(signature_url, 95, 54)
            
    firma_bytes = None
    if firma_org_url:
        try:
            resp = requests.get(firma_org_url, timeout=10)
            if resp.status_code == 200:
                firma_bytes = process_transparency(resp.content)
        except: pass
        
    def get_firma_vet(v_url=None):
        if v_url:
            img = fetch_image(v_url, 90, 40)
            if img: return img
        if firma_bytes:
            return Image(io.BytesIO(firma_bytes), width=90, height=40)
        return global_sig_img or ""

    def get_firma_sello(v_url=None):
        if v_url:
            img = fetch_image(v_url, 95, 54)
            if img: return img
        if global_sig_stamp_img:
            return global_sig_stamp_img
        if firma_bytes:
            return Image(io.BytesIO(firma_bytes), width=95, height=54)
        return ""

    # --- SECCIÓN 1: PLAN SANITARIO (VACUNAS) ---
    elements.append(Paragraph("<b>PLAN SANITARIO</b>", styles['Heading3']))
    
    # Clasificación de registros (Keywords expandidas)
    vac_keywords = ["vacuna", "quintuple", "sextuple", "rabia", "tos", "giardia", "leucemia", "parvovirus", "moquillo", "refuerzo", "dosis", "antigena"]
    desp_keywords = ["desparasita", "antiparasit", "pipeta", "comprimido", "simparica", "nexgard", "bravecto", "total full", "totalfull", "drontal", "apredislon", "masticable"]
    
    # Headers logic
    if is_digital:
        vac_data = [["FECHA", "VACUNA", "LOTE", "FIRMA VET.", "PRÓX. VACUNA"]]
    else:
        vac_data = [["FECHA", "VACUNA", "FIRMA Y SELLO", "PRÓX. VACUNA"]]
        
    desp_data = [["FECHA", "PESO", "TRATAMIENTO", "FIRMA Y SELLO"]]
    
    has_vac = False
    has_desp = False
    
    for v in vaccinations:
        name_lower = v.vaccine_name.lower()
        fecha = v.date_administered.strftime("%d/%m/%Y")
        prox = v.next_dose_date.strftime("%d/%m/%Y") if v.next_dose_date else "-"
        is_desp = any(k in name_lower for k in desp_keywords)
        
        if is_desp:
            weight_str = f"{patient_weight} kg" if patient_weight else "-"
            # Firma en la fila de desparasitación (160x90 config)
            firma_row = get_firma_sello(v.signature_hash) if is_digital else ""
            desp_data.append([fecha, weight_str, Paragraph(v.vaccine_name, styles['Normal']), firma_row])
            has_desp = True
        else:
            if is_digital:
                # Digital Row
                lote = v.batch_number if v.batch_number else "-"
                
                # Check for stamp/signature data stored in the vaccination record
                signature_info = ""
                if v.signature_data:
                    signature_info = v.signature_data
                elif v.is_signed:
                    signature_info = "Firmado Digitalmente"
                
                # Use image if available, else text (90x40 config)
                firma_cell = get_firma_vet(v.signature_hash) or Paragraph(signature_info, styles['Normal'])
                
                vac_data.append([fecha, Paragraph(v.vaccine_name, styles['Normal']), lote, firma_cell, prox])
            else:
                # Basic Row
                vac_data.append([fecha, Paragraph(v.vaccine_name, styles['Normal']), get_firma_sello(v.signature_hash), prox])
            has_vac = True

    # Estilos usando org_colors
    header_bg = colors.HexColor(primary_color)
    row_bg = colors.HexColor(secondary_color)
    
    if is_digital:
        col_widths_vac = [1*inch, 2*inch, 1*inch, 1.5*inch, 1*inch]
    else:
        col_widths_vac = [1.2*inch, 2.3*inch, 1.8*inch, 1.2*inch]

    
    # Renderizar Tabla de Vacunas
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), row_bg),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ])

    if has_vac:
        t_vac = Table(vac_data, colWidths=col_widths_vac)
        t_vac.setStyle(t_style)
        elements.append(t_vac)
    else:
        elements.append(Paragraph("<i>No hay vacunas registradas.</i>", styles['Normal']))

    elements.append(Spacer(1, 25))

    # --- SECCIÓN 2: DESPARASITACIÓN ---
    elements.append(Paragraph("<b>DESPARASITACIÓN (Interna / Externa)</b>", styles['Heading3']))
    
    if has_desp:
        t_desp = Table(desp_data, colWidths=[1.2*inch, 1*inch, 2.5*inch, 1.8*inch])
        t_desp_style = TableStyle([
             ('BACKGROUND', (0, 0), (-1, 0), header_bg),
             ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
             ('BACKGROUND', (0, 1), (-1, -1), row_bg),
             ('GRID', (0, 0), (-1, -1), 1, colors.white),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
             ('FONTSIZE', (0, 0), (-1, -1), 9),
             ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
             ('TOPPADDING', (0, 0), (-1, -1), 6),
        ])
        
        t_desp.setStyle(t_desp_style)
        elements.append(t_desp)
    else:
        elements.append(Paragraph("<i>No hay tratamientos de desparasitación registrados.</i>", styles['Normal']))

    elements.append(Spacer(1, 40))
    
    # Digital Legend Footer (Minimalist)
    if is_digital:
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceBefore=10, spaceAfter=10))
        footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], fontSize=7, textColor=colors.grey, alignment=1)
        elements.append(Paragraph("Este documento es un registro oficial generado digitalmente. La autenticidad puede verificarse escaneando el código QR superior.", footer_style))
    else:
        elements.append(Paragraph("<i>Este documento es un registro oficial de la clínica. Los sellos y firmas físicos validan la aplicación de cada dosis.</i>", styles['Normal']))
    
    doc.build(elements, onFirstPage=lambda c, d: draw_watermark(c, d, org_name))
    buffer.seek(0)
    return buffer

def generate_prescription_pdf(org_name, patient_name, medication_text):
    """Receta médica digital."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements, styles = _get_base_elements(org_name, "RECETA MÉDICA / RP:")

    elements.append(Paragraph(f"<b>PACIENTE:</b> {patient_name.upper()}", styles['Normal']))
    elements.append(Paragraph(f"<b>FECHA:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Spacer(1, 30))

    # Styling for the RP: content
    rp_style = ParagraphStyle('RPStyle', parent=styles['Normal'], fontSize=12, leading=16)
    elements.append(Paragraph(medication_text.replace("\n", "<br/>"), rp_style))
    
    elements.append(Spacer(1, 100))
    elements.append(HRFlowable(width="30%", thickness=1, color=colors.black, alignment=1))
    elements.append(Paragraph("Firma Masaje Profesional", styles['Normal'])) # Mocking professional footer

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_invoice_pdf(org_name, customer_name, items, total):
    """Factura de servicios veterinarios."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements, styles = _get_base_elements(org_name, "COMPROBANTE DE SERVICIOS")

    elements.append(Paragraph(f"<b>CLIENTE:</b> {customer_name}", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["DESCRIPCIÓN", "CANTIDAD", "UNITARIO", "TOTAL"]]
    for item in items:
        data.append([item['desc'], item['qty'], f"${item['price']}", f"${item['qty'] * item['price']}"])

    data.append(["", "", "<b>TOTAL</b>", f"<b>${total}</b>"])

    t = Table(data, colWidths=[3.5*inch, 1*inch, 1*inch, 1*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F6F4F0")),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#2E5077")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
    ]))
    
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_ticket_pdf(org, ticket, items, patient, owner, vet):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header
    elements.append(Paragraph(f"<b>{org.name}</b>", styles['Title']))
    elements.append(Paragraph(f"TICKET #{ticket.ticket_number}", styles['Heading2']))
    elements.append(Paragraph(f"Fecha: {ticket.date.strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Paragraph(f"Veterinario: {vet.username}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Patient Info
    elements.append(Paragraph(f"Paciente: {patient.name} ({patient.species}) | Tutor: {owner.name}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Items Table
    data = [["Descripción", "Cant", "Precio Unit", "Subtotal"]]
    for item in items:
        data.append([item.description, str(item.quantity), f"${item.unit_price:.2f}", f"${item.subtotal:.2f}"])
    
    # Result Row ("To Pay")
    data.append(["", "", "TOTAL", f"${ticket.total_amount:.2f}"])
    
    table = Table(data, colWidths=[300, 50, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (-2,-1), (-1,-1), 'Helvetica-Bold'), # Total row bold
    ]))
    elements.append(table)
    
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<i>Este ticket es un comprobante interno y no reemplaza un comprobante fiscal.</i>", styles['Italic']))
    
    doc.build(elements, onFirstPage=lambda c, d: draw_watermark(c, d, org.name))
    buffer.seek(0)
    return buffer
