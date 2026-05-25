from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "srm.db")

# ════════════════════════════════════════════
# COULEURS SRM — Style facture marocaine
# ════════════════════════════════════════════
BLEU_SRM     = colors.HexColor("#1e3155")
BLEU_CLAIR   = colors.HexColor("#eef2f9")
OR_SRM       = colors.HexColor("#d4a44a")
OR_CLAIR     = colors.HexColor("#fdf8ed")
VERT_SRM     = colors.HexColor("#2e7d32")
GRIS_TITRE   = colors.HexColor("#374151")
GRIS_TEXTE   = colors.HexColor("#4b5563")
GRIS_CLAIR   = colors.HexColor("#f9fafb")
GRIS_BORDURE = colors.HexColor("#e5e7eb")
BLANC        = colors.white

def _get_facture_data(numero_contrat: str, mois_source: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_client, adresse, agence, usage, type_service,
               numero_contrat, numero_client, numero_compteur,
               periode_debut, periode_fin, date_limite_paiement,
               consommation, unite, montant_ttc, mois_source
        FROM factures_excel
        WHERE numero_contrat = ? AND mois_source LIKE ?
        LIMIT 1
    """, (numero_contrat, f"%{mois_source}%"))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "nom_client"          : row[0],
        "adresse"             : row[1],
        "agence"              : row[2],
        "usage"               : row[3],
        "type_service"        : row[4],
        "numero_contrat"      : row[5],
        "numero_client"       : row[6],
        "numero_compteur"     : row[7],
        "periode_debut"       : row[8],
        "periode_fin"         : row[9],
        "date_limite_paiement": row[10],
        "consommation"        : row[11],
        "unite"               : row[12],
        "montant_ttc"         : row[13],
        "mois_source"         : row[14],
    }

def generer_pdf_facture(numero_contrat: str, mois_source: str) -> bytes | None:
    data = _get_facture_data(numero_contrat, mois_source)
    if not data:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    elements = []

    def style(name, **kwargs):
        return ParagraphStyle(name, **kwargs)

    style_normal = style("normal", fontSize=9, textColor=GRIS_TEXTE, fontName="Helvetica")
    style_bold   = style("bold",   fontSize=9, textColor=GRIS_TITRE, fontName="Helvetica-Bold")
    style_small  = style("small",  fontSize=7, textColor=GRIS_TEXTE, fontName="Helvetica")
    style_right  = style("right",  fontSize=9, textColor=GRIS_TEXTE, fontName="Helvetica", alignment=TA_RIGHT)
    style_center = style("center", fontSize=9, textColor=GRIS_TEXTE, fontName="Helvetica", alignment=TA_CENTER)
    style_title  = style("title",  fontSize=16, textColor=BLEU_SRM,  fontName="Helvetica-Bold")
    style_amount = style("amount", fontSize=18, textColor=VERT_SRM,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
    style_header = style("header", fontSize=8,  textColor=BLEU_SRM,  fontName="Helvetica-Bold", alignment=TA_CENTER)

    # ══════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════
    LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "srm_logo.png")

    if os.path.exists(LOGO_PATH):
        from reportlab.platypus import Image
        logo = Image(LOGO_PATH, width=3.2*cm, height=3.2*cm)
    else:
        logo = Paragraph("<b>SRM</b>", style_title)

    # Société
    company_info = Table([
        [Paragraph("<b>SRM Souss-Massa</b>", style("comp", fontSize=10, textColor=BLEU_SRM, fontName="Helvetica-Bold"))],
        [Paragraph("Société Régionale Multiservices", style_small)],
        [Paragraph(f"Agence : {data['agence']}", style_small)],
        [Paragraph("Tél : 05 28 XX XX XX", style_small)],
    ], colWidths=[6.5*cm])
    company_info.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
    ]))

    # Titre FACTURE
    title_block = Table([
        [Paragraph("FACTURE", style_title)],
        [Paragraph(data['mois_source'], style("periode", fontSize=9, textColor=OR_SRM, fontName="Helvetica-Bold"))],
    ], colWidths=[5*cm])
    title_block.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    # Références — avec espacement et bordure interne
    refs_data = [
        [Paragraph("N° Facture", style_bold), Paragraph(data["numero_client"], style_normal)],
        [Paragraph("N° Contrat", style_bold), Paragraph(data["numero_contrat"], style_normal)],
        [Paragraph("N° Compteur", style_bold), Paragraph(data["numero_compteur"], style_normal)],
        [Paragraph("Date d'émission", style_bold), Paragraph(data["mois_source"], style_normal)],
    ]
    
    refs_table = Table(refs_data, colWidths=[3.8*cm, 6*cm])
    refs_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("ALIGN", (1,0), (1,-1), "LEFT"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (0,-1), 5),
        ("LEFTPADDING", (1,0), (1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("BOX", (0,0), (-1,-1), 0.5, GRIS_BORDURE),
        ("BACKGROUND", (0,0), (-1,-1), GRIS_CLAIR),
    ]))
    
    # Assemblage header avec marges internes
    header_table = Table(
        [[logo, company_info, title_block, refs_table]], 
        colWidths=[3.8*cm, 6.5*cm, 5*cm, 9.8*cm]
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (2,0), (2,0), "CENTER"),
        ("ALIGN", (3,0), (3,0), "LEFT"),
        ("LEFTPADDING", (3,0), (3,0), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=BLEU_SRM, spaceAfter=0.3*cm))

    # ══════════════════════════════════════════
    # INFORMATIONS CLIENT
    # ══════════════════════════════════════════
    elements.append(Paragraph("INFORMATIONS CLIENT", style("section", fontSize=10, textColor=BLEU_SRM, fontName="Helvetica-Bold")))
    elements.append(Spacer(1, 0.2*cm))

    client_data = [
        [Paragraph("<b>Nom</b>", style_bold), Paragraph(data["nom_client"], style_normal), 
         Paragraph("<b>Usage</b>", style_bold), Paragraph(data["usage"], style_normal)],
        [Paragraph("<b>Adresse</b>", style_bold), Paragraph(data["adresse"], style_normal),
         Paragraph("<b>Type service</b>", style_bold), Paragraph(data["type_service"], style_normal)],
    ]
    client_table = Table(client_data, colWidths=[2.2*cm, 6.3*cm, 2.2*cm, 6.3*cm])
    client_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLANC),
        ("BOX", (0,0), (-1,-1), 0.5, GRIS_BORDURE),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════
    # PÉRIODE
    # ══════════════════════════════════════════
    elements.append(Paragraph("PÉRIODE DE CONSOMMATION", style("section", fontSize=10, textColor=BLEU_SRM, fontName="Helvetica-Bold")))
    elements.append(Spacer(1, 0.2*cm))

    periode_table = Table([
        [Paragraph(f"Du {data['periode_debut']} au {data['periode_fin']}", style_normal)]
    ], colWidths=[17*cm])
    periode_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GRIS_CLAIR),
        ("BOX", (0,0), (-1,-1), 0.5, GRIS_BORDURE),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    elements.append(periode_table)
    elements.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════
    # DÉTAIL
    # ══════════════════════════════════════════
    elements.append(Paragraph("DÉTAIL DE LA FACTURE", style("section", fontSize=10, textColor=BLEU_SRM, fontName="Helvetica-Bold")))
    elements.append(Spacer(1, 0.2*cm))

    unite = data["unite"]
    conso = data["consommation"]
    montant = data["montant_ttc"]
    tva_rate = 0.14
    montant_ht = round(montant / (1 + tva_rate), 2)
    tva = round(montant - montant_ht, 2)
    prix_unitaire = montant_ht / max(conso, 0.01)

    detail_data = [
        [Paragraph("<b>Désignation</b>", style_header),
         Paragraph("<b>Quantité</b>", style_header),
         Paragraph("<b>Prix unitaire (Dhs)</b>", style_header),
         Paragraph("<b>Montant (Dhs)</b>", style_header)],
        [Paragraph("Consommation d'énergie", style_normal),
         Paragraph(f"{conso:,.2f} {unite}", style_center),
         Paragraph(f"{prix_unitaire:,.3f}", style_right),
         Paragraph(f"{montant_ht:,.2f}", style_right)],
        [Paragraph("TVA (14%)", style_normal),
         Paragraph("", style_center),
         Paragraph("", style_right),
         Paragraph(f"{tva:,.2f}", style_right)],
    ]
    detail_table = Table(detail_data, colWidths=[7*cm, 3.5*cm, 4*cm, 4*cm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BLEU_SRM),
        ("TEXTCOLOR", (0,0), (-1,0), BLANC),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [BLANC, GRIS_CLAIR]),
        ("BOX", (0,0), (-1,-1), 0.5, GRIS_BORDURE),
        ("GRID", (0,0), (-1,-2), 0.3, GRIS_BORDURE),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("ALIGN", (1,1), (1,-1), "CENTER"),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 0.2*cm))

    # ══════════════════════════════════════════
    # TOTAL
    # ══════════════════════════════════════════
    total_data = [
        [Paragraph("TOTAL TTC", style("total_label", fontSize=12, textColor=BLEU_SRM, fontName="Helvetica-Bold")),
         Paragraph(f"{montant:,.2f} Dhs", style_amount)],
    ]
    total_table = Table(total_data, colWidths=[10*cm, 7*cm])
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), OR_CLAIR),
        ("BOX", (0,0), (-1,-1), 1.2, OR_SRM),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 20),
        ("RIGHTPADDING", (0,0), (-1,-1), 20),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
    ]))
    elements.append(total_table)
    elements.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════
    # DATE LIMITE
    # ══════════════════════════════════════════
    dlp_table = Table([
        [Paragraph(f"⚠️  Date limite de paiement : {data['date_limite_paiement']}", 
                   style("dlp", fontSize=9, textColor=VERT_SRM, fontName="Helvetica-Bold"))]
    ], colWidths=[17*cm])
    dlp_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#e8f5e9")),
        ("BOX", (0,0), (-1,-1), 0.5, VERT_SRM),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    elements.append(dlp_table)
    elements.append(Spacer(1, 0.3*cm))

    # ══════════════════════════════════════════
    # PAIEMENT
    # ══════════════════════════════════════════
    payment_info = Table([
        [Paragraph("<b>Moyens de paiement acceptés</b>", style_bold)],
        [Paragraph("• Virement bancaire", style_small)],
        [Paragraph("• Espèces dans nos agences", style_small)],
        [Paragraph("• Chèque barré à l'ordre de SRM", style_small)],
    ], colWidths=[17*cm])
    payment_info.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(payment_info)

    # ══════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_BORDURE))
    
    footer_text = f"""
    <font size=7 color='#6b7280'>
    SRM Souss-Massa — Agence {data['agence']} | www.srm.ma | contact@srm.ma
    <br/>Document généré automatiquement — Merci de votre confiance
    </font>
    """
    footer = Paragraph(footer_text, style_center)
    elements.append(footer)

    doc.build(elements)
    return buffer.getvalue()