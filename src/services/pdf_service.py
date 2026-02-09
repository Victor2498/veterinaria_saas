from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from datetime import datetime
import io

def _get_base_elements(org_name, title):
    """Helper to create professional header for all PDFs."""
    styles = getSampleStyleSheet()
    elements = []
    
    # Header styled as a professional letterhead
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor("#2E5077"),
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

def generate_vaccination_certificate(org_name, patient_name, vaccinations, patient_weight=None):
    """Certificado oficial de vacunación con formato de libreta sanitaria."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements, styles = _get_base_elements(org_name, "LIBRETA SANITARIA")

    elements.append(Paragraph(f"<b>PACIENTE:</b> {patient_name.upper()}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # --- SECCIÓN 1: PLAN SANITARIO (VACUNAS) ---
    elements.append(Paragraph("<b>PLAN SANITARIO</b>", styles['Heading3']))
    
    # Clasificación de registros
    vac_keywords = ["quintuple", "sextuple", "rabia", "tos", "giardia", "leucemia", "parvovirus", "moquillo"]
    desp_keywords = ["desparasita", "antiparasit", "pipeta", "comprimido", "simparica", "nexgard", "bravecto", "total full"]
    
    vac_data = [["FECHA", "VACUNA", "FIRMA Y SELLO", "PRÓX. VACUNA"]]
    desp_data = [["FECHA", "PESO", "TRATAMIENTO", "FIRMA Y SELLO"]]
    
    has_vac = False
    has_desp = False
    
    for v in vaccinations:
        name_lower = v.vaccine_name.lower()
        fecha = v.date_administered.strftime("%d/%m/%Y")
        prox = v.next_dose_date.strftime("%d/%m/%Y") if v.next_dose_date else "-"
        
        # Lógica de clasificación
        is_desp = any(kw in name_lower for kw in desp_keywords)
        
        if is_desp:
            weight_str = f"{patient_weight} kg" if patient_weight else "-"
            desp_data.append([fecha, weight_str, Paragraph(v.vaccine_name, styles['Normal']), ""])
            has_desp = True
        else:
            vac_data.append([fecha, Paragraph(v.vaccine_name, styles['Normal']), "", prox])
            has_vac = True

    # Estilo Naranja/Ocre inspirado en la imagen
    ocre_color = colors.HexColor("#F9D5B1")
    ocre_header = colors.HexColor("#E38E49")
    
    # Renderizar Tabla de Vacunas
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ocre_header),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), ocre_color),
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ])

    if has_vac:
        t_vac = Table(vac_data, colWidths=[1.2*inch, 2.3*inch, 1.8*inch, 1.2*inch])
        t_vac.setStyle(t_style)
        elements.append(t_vac)
    else:
        elements.append(Paragraph("<i>No hay vacunas registradas.</i>", styles['Normal']))

    elements.append(Spacer(1, 25))

    # --- SECCIÓN 2: DESPARASITACIÓN ---
    elements.append(Paragraph("<b>DESPARASITACIÓN (Interna / Externa)</b>", styles['Heading3']))
    
    if has_desp:
        t_desp = Table(desp_data, colWidths=[1.2*inch, 1*inch, 2.5*inch, 1.8*inch])
        t_desp.setStyle(t_style)
        elements.append(t_desp)
    else:
        elements.append(Paragraph("<i>No hay tratamientos de desparasitación registrados.</i>", styles['Normal']))

    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<i>Este documento es un registro oficial de la clínica. Los sellos y firmas físicos validan la aplicación de cada dosis.</i>", styles['Normal']))
    
    doc.build(elements)
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
