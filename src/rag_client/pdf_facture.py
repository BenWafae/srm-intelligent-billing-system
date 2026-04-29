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
# COULEURS SRM
# ════════════════════════════════════════════
VERT_SRM    = colors.HexColor("#2E7D32")
VERT_CLAIR  = colors.HexColor("#E8F5E9")
GRIS_CLAIR  = colors.HexColor("#F5F5F5")
GRIS_TITRE  = colors.HexColor("#424242")
BLANC       = colors.white
NOIR        = colors.black

# ════════════════════════════════════════════
# FETCH DONNÉES
# ════════════════════════════════════════════
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

# ════════════════════════════════════════════
# GÉNÉRATION PDF
# ════════════════════════════════════════════
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

    styles = getSampleStyleSheet()
    elements = []

    # ── Style helpers ──
    def style(name, **kwargs):
        s = ParagraphStyle(name, **kwargs)
        return s

    titre_style   = style("titre",   fontSize=11, textColor=GRIS_TITRE, fontName="Helvetica-Bold")
    normal_style  = style("normal",  fontSize=9,  textColor=NOIR,       fontName="Helvetica")
    small_style   = style("small",   fontSize=8,  textColor=GRIS_TITRE, fontName="Helvetica")
    right_style   = style("right",   fontSize=9,  textColor=NOIR,       fontName="Helvetica", alignment=TA_RIGHT)
    center_style  = style("center",  fontSize=9,  textColor=NOIR,       fontName="Helvetica", alignment=TA_CENTER)
    big_style     = style("big",     fontSize=14, textColor=BLANC,      fontName="Helvetica-Bold", alignment=TA_CENTER)
    header_style  = style("header",  fontSize=10, textColor=BLANC,      fontName="Helvetica-Bold")

    # ══════════════════════════════════════════
    # HEADER — Logo + Références
    # ══════════════════════════════════════════
    LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "logo_srm.png")

    if os.path.exists(LOGO_PATH):
        from reportlab.platypus import Image
        logo = Image(LOGO_PATH, width=4*cm, height=2*cm)
    else:
        logo = Paragraph("<b>SRM</b>", titre_style)

    refs = Table([
        [Paragraph("Références",    small_style),  Paragraph(data["numero_contrat"], normal_style)],
        [Paragraph("N° Facture",    small_style),  Paragraph(data["numero_client"],  normal_style)],
        [Paragraph("Agence",        small_style),  Paragraph(data["agence"],         normal_style)],
    ], colWidths=[3*cm, 6*cm])
    refs.setStyle(TableStyle([
        ("ALIGN",       (0,0), (-1,-1), "LEFT"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [GRIS_CLAIR, BLANC]),
        ("BOX",         (0,0), (-1,-1), 0.5, colors.grey),
    ]))

    header_table = Table([[logo, refs]], colWidths=[8*cm, 9*cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",  (1,0), (1,0),  "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════════════════
    # TITRE FACTURE
    # ══════════════════════════════════════════
    titre_table = Table(
        [[Paragraph(f"Avis de Facturation — {data['mois_source']}", big_style)]],
        colWidths=[17*cm]
    )
    titre_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), VERT_SRM),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(titre_table)
    elements.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════
    # INFOS CLIENT
    # ══════════════════════════════════════════
    client_data = [
        [Paragraph("<b>Informations Client</b>", header_style), ""],
        [Paragraph("Nom",           small_style), Paragraph(data["nom_client"],      normal_style)],
        [Paragraph("Adresse",       small_style), Paragraph(data["adresse"],         normal_style)],
        [Paragraph("N° Client",     small_style), Paragraph(data["numero_client"],   normal_style)],
        [Paragraph("N° Contrat",    small_style), Paragraph(data["numero_contrat"],  normal_style)],
        [Paragraph("N° Compteur",   small_style), Paragraph(data["numero_compteur"], normal_style)],
        [Paragraph("Usage",         small_style), Paragraph(data["usage"],           normal_style)],
        [Paragraph("Type Service",  small_style), Paragraph(data["type_service"],    normal_style)],
    ]
    client_table = Table(client_data, colWidths=[4*cm, 13*cm])
    client_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), VERT_SRM),
        ("TEXTCOLOR",     (0,0), (-1,0), BLANC),
        ("SPAN",          (0,0), (-1,0)),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [GRIS_CLAIR, BLANC]),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.grey),
        ("GRID",          (0,1), (-1,-1), 0.3, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════
    # PÉRIODE
    # ══════════════════════════════════════════
    periode_table = Table([
        [
            Paragraph("<b>Période de consommation</b>", header_style),
            Paragraph(f"du  {data['periode_debut']}  au  {data['periode_fin']}", normal_style)
        ]
    ], colWidths=[7*cm, 10*cm])
    periode_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,0), VERT_SRM),
        ("BACKGROUND",    (1,0), (1,0), VERT_CLAIR),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.grey),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    elements.append(periode_table)
    elements.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════
    # DÉTAIL CONSOMMATION
    # ══════════════════════════════════════════
    unite = data["unite"]
    conso = data["consommation"]
    montant = data["montant_ttc"]
    tva_rate = 0.14
    montant_ht = round(montant / (1 + tva_rate), 2)
    tva = round(montant - montant_ht, 2)

    conso_data = [
        [
            Paragraph("<b>Désignation</b>",       header_style),
            Paragraph("<b>Consommation</b>",       header_style),
            Paragraph("<b>Montant (Dhs)</b>",      header_style),
        ],
        [
            Paragraph(f"Énergie ({unite})",        normal_style),
            Paragraph(f"{conso:,.2f} {unite}",     normal_style),
            Paragraph(f"{montant_ht:,.2f}",        right_style),
        ],
        [
            Paragraph("TVA (14%)",                 normal_style),
            Paragraph("",                          normal_style),
            Paragraph(f"{tva:,.2f}",               right_style),
        ],
        [
            Paragraph("<b>Sous-total TTC</b>",     titre_style),
            Paragraph("",                          normal_style),
            Paragraph(f"<b>{montant:,.2f}</b>",    right_style),
        ],
    ]
    conso_table = Table(conso_data, colWidths=[8*cm, 5*cm, 4*cm])
    conso_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), VERT_SRM),
        ("TEXTCOLOR",     (0,0), (-1,0), BLANC),
        ("ROWBACKGROUNDS",(0,1), (-1,-2), [GRIS_CLAIR, BLANC]),
        ("BACKGROUND",    (0,-1),(-1,-1), VERT_CLAIR),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.grey),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ALIGN",         (2,0), (2,-1), "RIGHT"),
    ]))
    elements.append(conso_table)
    elements.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════
    # NET À PAYER
    # ══════════════════════════════════════════
    net_table = Table([
        [
            Paragraph("<b>NET À PAYER</b>", big_style),
            Paragraph(f"<b>{montant:,.2f} Dhs</b>", big_style),
        ]
    ], colWidths=[10*cm, 7*cm])
    net_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), VERT_SRM),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 1, VERT_SRM),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 0.4*cm))

    # ══════════════════════════════════════════
    # DATE LIMITE
    # ══════════════════════════════════════════
    dlp_table = Table([
        [
            Paragraph("⚠️  Date limite de paiement :", normal_style),
            Paragraph(f"<b>{data['date_limite_paiement']}</b>", titre_style),
        ]
    ], colWidths=[8*cm, 9*cm])
    dlp_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#FFF9C4")),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.orange),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    elements.append(dlp_table)
    elements.append(Spacer(1, 0.8*cm))

    # ══════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2*cm))
    footer = Paragraph(
        f"<font size=7 color='grey'>"
        f"SRM — {data['agence']} | www.srm-cs.ma | contact@srm-cs.ma | "
        f"Document généré automatiquement — {data['mois_source']}"
        f"</font>",
        center_style
    )
    elements.append(footer)

    doc.build(elements)
    return buffer.getvalue()