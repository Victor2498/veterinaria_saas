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

def generate_vaccination_certificate(org_name, patient_name, vaccinations):
    """Certificado oficial de vacunación."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements, styles = _get_base_elements(org_name, "CERTIFICADO DE VACUNACIÓN")

    elements.append(Paragraph(f"Por la presente se certifica que el paciente <b>{patient_name.upper()}</b> ha recibido las siguientes inmunizaciones:", styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["VACUNA / ANTÍGENO", "FECHA APLICACIÓN", "PRÓXIMA DOSIS"]]
    for v in vaccinations:
        next_dose = v.next_dose_date.strftime("%d/%m/%Y") if v.next_dose_date else "N/A"
        data.append([v.vaccine_name, v.date_administered.strftime("%d/%m/%Y"), next_dose])

    t = Table(data, colWidths=[2.5*inch, 2*inch, 2*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#79D7BE")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2E5077")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("__________________________", styles['Normal']))
    elements.append(Paragraph(f"Firma y Sello - {org_name}", styles['Normal']))
    
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
