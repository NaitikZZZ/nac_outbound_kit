"""Generate a PDF summary of Interakt WhatsApp templates/campaigns (Apr 2026 - present)."""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

OUT_PATH = "outputs/interakt-whatsapp-campaigns/Interakt_WhatsApp_Campaigns_Apr2026_Aug2026.pdf"

DATA = [
    ("2026-04-09", "CHRO CONFEX"),
    ("2026-04-13", "NetCore BFSI"),
    ("2026-04-13", "HRs accounts greaters than 500"),
    ("2026-04-17", "P3_ABM_GPTW_SUBSEQUENT_WINNERS_CX"),
    ("2026-04-21", "NetCore_Tech"),
    ("2026-04-21", "NetCore_MAnufacturing"),
    ("2026-05-28", "Moengage Summit"),
    ("2026-06-23", "CHRO 10 june attendees"),
    ("2026-06-23", "CHRO 10 june non attendees"),
    ("2026-06-23", "CHRO Confex during event"),
    ("2026-07-06", "NHRDA DURING event"),
    ("2026-07-20", "Brand world Summit During event"),
    ("2026-07-20", "Brand world summit post event"),
    ("2026-07-21", "NHRD post event"),
    ("2026-07-21", "DCX"),
    ("2026-07-21", "Financial Express HR Summit Empuls - Met at event"),
    ("2026-07-21", "Financial Express HR Summit Empuls - Missed at event"),
    ("2026-07-24", "Copy of people_excellenc"),
    ("2026-07-30", "DCX Post event"),
    ("2026-07-30", "DCX speakers"),
    ("2026-08-17", "P0_EVNT_Carrots and StakesXWebEngage_Gurugram"),
    ("2026-08-18", "Post Event leads - SHRM Unconference"),
    ("2026-08-18", "Redemption Voucher"),
    ("2026-08-18", "CMO Mixer"),
    ("2026-08-19", "Post event"),
]

styles = getSampleStyleSheet()
doc = SimpleDocTemplate(OUT_PATH, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
story = []

story.append(Paragraph("Interakt WhatsApp Campaigns", styles["Title"]))
story.append(Paragraph("April 2026 - August 2026", styles["Heading3"]))
story.append(Spacer(1, 12))
story.append(Paragraph(
    "Source: Interakt approved WhatsApp templates (GET /track/organization/templates). "
    "Interakt's public API has no dedicated \"list campaigns\" endpoint, so the template "
    "list is used as a proxy for campaigns run - it reflects template creation dates, "
    "not send/delivery counts.",
    styles["Normal"],
))
story.append(Spacer(1, 16))

table_data = [["Date Created", "Template / Campaign"]] + list(DATA)
table = Table(table_data, colWidths=[1.3 * inch, 5.2 * inch], repeatRows=1)
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d2d2d")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(table)
story.append(Spacer(1, 16))
story.append(Paragraph(f"Total: {len(DATA)} campaigns/templates", styles["Normal"]))

doc.build(story)
print(f"Wrote {OUT_PATH}")
