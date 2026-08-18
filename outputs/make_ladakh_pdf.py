#!/usr/bin/env python3
"""Generate the sā Ladakh Biennale 2026 budget trip plan PDF."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

OUT = "outputs/Ladakh-Biennale-2026-Budget-Trip-Plan.pdf"

# Palette: high-altitude / earthy
INK = colors.HexColor("#1f2933")
ACCENT = colors.HexColor("#9c4221")      # terracotta
ACCENT2 = colors.HexColor("#2c5282")     # himalayan blue
SOFT = colors.HexColor("#f5efe6")        # warm sand
SOFT2 = colors.HexColor("#eaf0f6")       # cool tint
LINE = colors.HexColor("#d6ccbb")
MUTED = colors.HexColor("#5b6670")

styles = getSampleStyleSheet()

H1 = ParagraphStyle("H1", parent=styles["Title"], fontName="Helvetica-Bold",
                    fontSize=24, textColor=INK, spaceAfter=2, leading=27, alignment=TA_LEFT)
SUB = ParagraphStyle("SUB", parent=styles["Normal"], fontName="Helvetica",
                     fontSize=11, textColor=ACCENT, spaceAfter=2, leading=15)
META = ParagraphStyle("META", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=9, textColor=MUTED, spaceAfter=10, leading=13)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13.5, textColor=ACCENT2, spaceBefore=14, spaceAfter=6, leading=16)
BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=10, textColor=INK, leading=15, spaceAfter=5)
BULLET = ParagraphStyle("BULLET", parent=BODY, leftIndent=12, bulletIndent=2, spaceAfter=3)
CELL = ParagraphStyle("CELL", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=9, textColor=INK, leading=12)
CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")
CELLW = ParagraphStyle("CELLW", parent=CELL, textColor=colors.white, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("NOTE", parent=BODY, fontSize=9.5, textColor=MUTED)
FOOT = ParagraphStyle("FOOT", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=7.5, textColor=MUTED, leading=10)

story = []

# ---- Header ----
story.append(Paragraph("sā Ladakh Biennale 2026", H1))
story.append(Paragraph("“Signals from Another Star”  &nbsp;•&nbsp;  Overland budget plan from Ahmedabad (train + shared transport)", SUB))
story.append(Paragraph("1–10 August 2026  &nbsp;•&nbsp;  Leh–Kargil corridor, Ladakh, India  &nbsp;•&nbsp;  Free &amp; non-ticketed", META))
story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceAfter=10))

# ---- Essentials table ----
story.append(Paragraph("The essentials", H2))
ess = [
    [Paragraph("Event", CELLB), Paragraph("sā Ladakh Biennale 2026, Aug 1–10", CELL)],
    [Paragraph("Entry", CELLB), Paragraph("Free, non-ticketed (no booking needed)", CELL)],
    [Paragraph("Biennale route", CELLB), Paragraph("Leh → Likir/Alchi → Lamayuru → Mulbekh → Kargil", CELL)],
    [Paragraph("How you travel", CELLB), Paragraph("Train Ahmedabad→Delhi, then shared/public bus + shared taxi via Manali to Leh", CELL)],
    [Paragraph("From Ahmedabad", CELLB), Paragraph("Overland, no personal vehicle. ~4–5 days each way", CELL)],
    [Paragraph("Altitude", CELLB), Paragraph("Manali 2,050m → Keylong 3,080m → Leh 3,500m (passes to 5,328m)", CELL)],
]
t = Table(ess, colWidths=[36*mm, 130*mm])
t.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (0, -1), SOFT),
    ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, SOFT2]),
    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(t)

# ---- Getting there (overland) ----
story.append(Paragraph("Overland route: train + shared transport", H2))
for label, txt in [
    ("1. Ahmedabad → Delhi (train, overnight)",
     "<b>Ashram Express (12915)</b> dep ~18:30, arr Delhi ~10:10 (~14–15h); or the faster <b>Rajdhani (12957)</b> ~12h. "
     "Fares: Sleeper ~₹450, 3AC ~₹1,300, 2AC ~₹1,900."),
    ("2. Delhi → Manali (shared/public Volvo bus, overnight)",
     "HRTC or private AC Volvo, evening departure, ~12h, arrives Manali early morning. Fare ₹1,000–1,500. "
     "Manali (~2,050m) is itself a useful first acclimatization step."),
    ("3. Manali → Leh (shared, 2 days — the key altitude leg)",
     "Take the <b>2-day HRTC deluxe bus</b> or a <b>shared taxi (Tata Sumo/Force, pooled by seat)</b> with an overnight "
     "halt at <b>Keylong (~3,080m)</b>. Day A: Manali → Keylong (Atal Tunnel). Day B: Keylong → Leh over Baralacha La "
     "and Tanglang La (5,328m). Fare: 2-day bus ₹1,200–1,800 incl. halt; shared-taxi seat ₹2,500–3,500."),
]:
    story.append(Paragraph(f"• <b>{label}:</b> {txt}", BULLET))

warn = Table([[Paragraph(
    "<b>⚠ Altitude warning:</b> the Manali–Leh road climbs past 5,000m very fast. The <b>Keylong overnight is "
    "non-negotiable</b>, and you still need a full rest day in Leh. The gentler route is Srinagar→Kargil→Leh, but that "
    "is awkward by shared vehicle from Delhi, so Manali is the right call for an overland shared trip.", BODY)]],
    colWidths=[166*mm])
warn.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fbeae5")),
    ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
    ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(Spacer(1, 2))
story.append(warn)

# ---- Itinerary ----
story.append(Paragraph("Suggested 13-day overland itinerary", H2))
itin = [
    [Paragraph("Day", CELLW), Paragraph("Plan", CELLW), Paragraph("Sleep", CELLW)],
    [Paragraph("1", CELLB), Paragraph("Ahmedabad → Delhi by overnight train (Ashram Exp / Rajdhani).", CELL), Paragraph("On train", CELL)],
    [Paragraph("2", CELLB), Paragraph("Arrive Delhi AM, rest. Evening: board shared Volvo bus to Manali.", CELL), Paragraph("On bus", CELL)],
    [Paragraph("3", CELLB), Paragraph("Arrive Manali AM. Acclimatize, rest (2,050m).", CELL), Paragraph("Manali", CELL)],
    [Paragraph("4", CELLB), Paragraph("Shared bus/taxi Manali → Keylong via Atal Tunnel. Acclimatization halt.", CELL), Paragraph("Keylong", CELL)],
    [Paragraph("5", CELLB), Paragraph("Shared bus/taxi Keylong → Leh (Baralacha La, Tanglang La 5,328m). Arrive eve.", CELL), Paragraph("Leh", CELL)],
    [Paragraph("6", CELLB), Paragraph("Leh — <b>full rest day</b> (altitude). Hydrate. Evening bazaar biennale venues.", CELL), Paragraph("Leh", CELL)],
    [Paragraph("7", CELLB), Paragraph("Leh city biennale: Leh Palace, Shanti Stupa, Namgyal Tsemo.", CELL), Paragraph("Leh", CELL)],
    [Paragraph("8", CELLB), Paragraph("Indus valley + art: Thiksey, Shey, Hemis, Stakna, plus installations.", CELL), Paragraph("Leh", CELL)],
    [Paragraph("9", CELLB), Paragraph("Shared taxi Leh → Likir → Alchi. 11th-c. murals + site-responsive works.", CELL), Paragraph("Alchi", CELL)],
    [Paragraph("10", CELLB), Paragraph("Alchi → Lamayuru. “Moonland” landscape, monastery, installations.", CELL), Paragraph("Lamayuru", CELL)],
    [Paragraph("11", CELLB), Paragraph("Lamayuru → Mulbekh → Kargil. Maitreya rock relief; western end of biennale.", CELL), Paragraph("Kargil", CELL)],
    [Paragraph("12", CELLB), Paragraph("Kargil → Leh by shared taxi. Mop up any corridor venues skipped.", CELL), Paragraph("Leh", CELL)],
    [Paragraph("13", CELLB), Paragraph("Return. <b>Fly Leh → Delhi</b> (saves ~2 days) then train onward; or overland Leh→Manali→Delhi (+3 days).", CELL), Paragraph("Home", CELL)],
]
t2 = Table(itin, colWidths=[12*mm, 130*mm, 24*mm])
t2.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), ACCENT2),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT2]),
    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(t2)
story.append(Spacer(1, 4))
story.append(Paragraph("Nights 1 and 2 are spent on the train and the bus, so they cost nothing in accommodation.", NOTE))

# ---- Budget stay plan ----
story.append(Paragraph("Budget stay plan (homestays, guesthouses, dorms)", H2))
stay = [
    [Paragraph("Night", CELLW), Paragraph("Place", CELLW), Paragraph("Stay type", CELLW), Paragraph("Rate (Aug peak)", CELLW)],
    [Paragraph("1", CELL), Paragraph("On overnight train", CELL), Paragraph("Sleeper / 3AC berth", CELL), Paragraph("(in fare)", CELL)],
    [Paragraph("2", CELL), Paragraph("On overnight bus", CELL), Paragraph("Volvo sleeper/semi-sleeper", CELL), Paragraph("(in fare)", CELL)],
    [Paragraph("3", CELL), Paragraph("Manali", CELL), Paragraph("Backpacker hostel / guesthouse", CELL), Paragraph("₹600–1,200", CELL)],
    [Paragraph("4", CELL), Paragraph("Keylong", CELL), Paragraph("Budget hotel / guesthouse", CELL), Paragraph("₹800–1,200", CELL)],
    [Paragraph("5–8", CELL), Paragraph("Leh (base)", CELL), Paragraph("Guesthouse / homestay", CELL), Paragraph("₹900–1,500", CELL)],
    [Paragraph("9", CELL), Paragraph("Alchi", CELL), Paragraph("Village homestay", CELL), Paragraph("₹800–1,500", CELL)],
    [Paragraph("10", CELL), Paragraph("Lamayuru", CELL), Paragraph("Homestay (often w/ meals)", CELL), Paragraph("₹700–1,200", CELL)],
    [Paragraph("11", CELL), Paragraph("Kargil", CELL), Paragraph("Budget hotel/guesthouse", CELL), Paragraph("₹1,150–1,800", CELL)],
    [Paragraph("12", CELL), Paragraph("Leh (same base)", CELL), Paragraph("Guesthouse", CELL), Paragraph("₹900–1,500", CELL)],
]
t3 = Table(stay, colWidths=[16*mm, 44*mm, 64*mm, 42*mm])
t3.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(t3)
story.append(Spacer(1, 5))
story.append(Paragraph(
    "<b>10 paid nights ≈ ₹9,000–14,500 total, solo</b> (2 nights are spent in transit). On twin-sharing it roughly halves per person.", BODY))

# ---- Smart money move (callout) ----
callout = Table([[Paragraph(
    "<b>Smart money move:</b> keep <b>one Leh guesthouse</b> for nights 5–8 and again night 12. Same bed, "
    "leave a bag there, and run the corridor (Alchi → Lamayuru → Kargil) with a light pack. Most Leh "
    "guesthouses hold luggage free and often give a repeat-stay discount.", BODY)]],
    colWidths=[166*mm])
callout.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), SOFT2),
    ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT2),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(callout)

# ---- Where to book ----
story.append(Paragraph("What to book where", H2))
for label, txt in [
    ("Leh (base)", "Stay in <b>Changspa</b> (backpacker hub, walkable to Shanti Stupa) or <b>Karzoo / Old Town</b>. "
                   "Private rooms ₹900–1,500; hostel dorms ~₹400–700/bed; homestays ₹600–1,200 with home-cooked food."),
    ("Alchi", "Small village, limited stock — book ahead. Skip the ₹3,000+ “resorts”; pick a <b>village homestay (₹800–1,500)</b> among the apricot orchards."),
    ("Lamayuru", "Cheapest stop. <b>Homestays ₹700–1,200</b>, usually with dinner + breakfast. Walk-in is fine except at peak."),
    ("Kargil", "More of a town. <b>Budget hotels/guesthouses ₹1,150–1,800</b>; homestays run cheaper."),
]:
    story.append(Paragraph(f"• <b>{label}:</b> {txt}", BULLET))

# ---- Booking tips ----
story.append(Paragraph("Booking tips for August (peak season)", H2))
for txt in [
    "<b>Book Leh + Alchi early.</b> August is busiest and the biennale adds demand; Leh rates run 20–40% above spring.",
    "<b>Lamayuru and Kargil</b> can be booked closer to the date or on arrival.",
    "<b>Carry cash.</b> Many homestays don’t take cards and ATMs are scarce past Leh — draw enough in Leh for the corridor.",
    "<b>Negotiate</b> multi-night and phone/walk-in rates; OTA prices are often higher.",
]:
    story.append(Paragraph(f"• {txt}", BULLET))

# ---- Permits + health (two columns) ----
permits = [Paragraph("<b>Permits</b>", BODY),
           Paragraph("Leh city + the Srinagar–Leh/Kargil corridor: no special permit for Indian citizens. "
                     "Adding Nubra / Pangong / Tso Moriri needs an <b>Inner Line Permit</b> via lahdclehpermit.in. "
                     "Foreign nationals book through a registered travel agent.", CELL)]
health = [Paragraph("<b>Packing &amp; health</b>", BODY),
          Paragraph("Warm layers (cold nights even in Aug), sturdy shoes, high-SPF sunscreen, sunglasses, rain shell, "
                    "reusable bottle. Ask your doctor about <b>Diamox</b>. Hydrate hard; skip alcohol the first 2 days.", CELL)]
two = Table([[permits[0]], [permits[1]]], colWidths=[81*mm])
twob = Table([[health[0]], [health[1]]], colWidths=[81*mm])
for tb in (two, twob):
    tb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
cols = Table([[two, twob]], colWidths=[83*mm, 83*mm])
cols.setStyle(TableStyle([("LEFTPADDING", (0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(0,0),4),
                          ("VALIGN",(0,0),(-1,-1),"TOP")]))
story.append(Paragraph("Permits, packing &amp; health", H2))
story.append(cols)

# ---- Contacts ----
story.append(Paragraph("On-the-ground contacts (official biennale travel coordinators)", H2))
for txt in [
    "Travel Light — Pranesh: +91 6295919671",
    "Curated Travel — Jigmet Wangchuk: +91 9419219783",
    "General inquiries: info@saladakh.com",
]:
    story.append(Paragraph(f"• {txt}", BULLET))

# ---- Transport costs ----
story.append(Paragraph("Transport cost (one way, shared/public)", H2))
tcost = [
    [Paragraph("Leg", CELLW), Paragraph("Mode", CELLW), Paragraph("Fare", CELLW)],
    [Paragraph("Ahmedabad → Delhi", CELL), Paragraph("Train (Sleeper / 3AC)", CELL), Paragraph("₹450 / ₹1,300", CELL)],
    [Paragraph("Delhi → Manali", CELL), Paragraph("Shared/public Volvo bus", CELL), Paragraph("₹1,000–1,500", CELL)],
    [Paragraph("Manali → Leh (2 days)", CELL), Paragraph("HRTC bus / shared taxi seat", CELL), Paragraph("₹1,200–3,500", CELL)],
    [Paragraph("Corridor + local", CELL), Paragraph("Shared taxis (pool seats)", CELL), Paragraph("₹3,000–6,000", CELL)],
]
t4 = Table(tcost, colWidths=[56*mm, 70*mm, 40*mm])
t4.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), ACCENT2),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT2]),
    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
]))
story.append(t4)

# ---- Budget summary ----
story.append(Paragraph("Rough total (budget tier, solo)", H2))
story.append(Paragraph(
    "Stays (10 paid nights) ₹9,000–14,500 &nbsp;•&nbsp; Overland transport one way ~₹5,500–12,000 (double for round trip, "
    "less if you fly Leh→Delhi back ~₹6,000–9,000) &nbsp;•&nbsp; Food ~₹500–800/day. "
    "Share taxi seats with other biennale-goers to cut the corridor cost hard. "
    "<b>Ballpark all-in: ₹30,000–55,000.</b>", BODY))

story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", thickness=0.7, color=LINE, spaceAfter=6))
story.append(Paragraph(
    "Prepared June 2026. Prices are indicative peak-season estimates in INR and will vary. Event details: sabiennale.com. "
    "Sources: sā Ladakh Biennale (sabiennale.com), Time Out India, Skyscanner, discoverwithdheeraj.com, ladakhdekho.com, homestaysofindia.com.",
    FOOT))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18*mm, 12*mm, "sā Ladakh Biennale 2026  •  Budget Trip Plan from Ahmedabad")
    canvas.drawRightString(A4[0]-18*mm, 12*mm, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=A4,
                        leftMargin=18*mm, rightMargin=18*mm,
                        topMargin=16*mm, bottomMargin=18*mm,
                        title="sā Ladakh Biennale 2026 - Budget Trip Plan",
                        author="Trip planner")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("WROTE", OUT)
