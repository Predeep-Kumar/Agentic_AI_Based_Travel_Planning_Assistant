from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime, timedelta


# INR FORMATTER (INDIAN COMMAS)

def format_inr(amount):
    try:
        amount = int(amount)
    except Exception:
        return amount

    s = str(amount)
    if len(s) <= 3:
        return s

    last3 = s[-3:]
    rest = s[:-3]

    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]

    if rest:
        parts.insert(0, rest)

    return ",".join(parts + [last3])



# STYLES

styles = getSampleStyleSheet()

TITLE = ParagraphStyle(
    "TITLE",
    parent=styles["Title"],
    fontSize=18,
    spaceAfter=14
)

SECTION = ParagraphStyle(
    "SECTION",
    parent=styles["Heading2"],
    fontSize=14,
    spaceBefore=16,
    spaceAfter=10
)

TEXT = ParagraphStyle(
    "TEXT",
    parent=styles["Normal"],
    fontSize=10,
    leading=14
)

BOLD = ParagraphStyle(
    "BOLD",
    parent=styles["Normal"],
    fontSize=10,
    leading=14,
    spaceAfter=4
)

# HELPER — BOXED TABLE

def boxed_table(data, widths):
    table = Table(data, colWidths=widths)
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


# MAIN PDF GENERATOR

def generate_trip_pdf(result: dict, output_path: str):

    if not result:
        return

    plan = result["TRIP_PLAN"]
    intent = result["FINAL_INTENT_JSON"]


    # DATE CALCULATION

    start_date = datetime.fromisoformat(intent["travel_date"])
    days = intent["days"]
    end_date = start_date + timedelta(days=days - 1)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []


    # TITLE

    story.append(Paragraph("AI Travel Planner – Trip Itinerary", TITLE))

    # TRIP OVERVIEW

    story.append(Paragraph("Trip Overview", SECTION))

    story.append(
        boxed_table(
            [[
                Paragraph(f"<b>Route</b><br/>{intent['source']} → {intent['destination']}", TEXT),
                Paragraph(f"<b>Duration</b><br/>{intent['days']} Days", TEXT),
                Paragraph(f"<b>Travelers</b><br/>{intent['travelers']}", TEXT),
            ]],
            [170, 170, 170]
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        boxed_table(
            [[
                Paragraph(f"<b>Trip Start</b><br/>{start_date.strftime('%d %b %Y (%A)')}", TEXT),
                Paragraph(f"<b>Trip End</b><br/>{end_date.strftime('%d %b %Y (%A)')}", TEXT),
            ]],
            [260, 260]
        )
    )


    # FLIGHTS

    story.append(Paragraph("Flights", SECTION))

    outbound = plan["FLIGHT"].get("outbound")
    return_flight = plan["FLIGHT"].get("return")

    outbound_cell = Paragraph(
        "<b>Outbound Flight</b><br/>"
        f"{outbound['flight_id']} ({outbound['airline']})<br/>"
        f"{outbound['from']} → {outbound['to']}<br/>"
        f"Departure: {start_date.strftime('%d %b %Y')}<br/>"
        f"Arrival: {start_date.strftime('%d %b %Y')}<br/>"
        f"Duration: {outbound['duration']}<br/>"
        f"Price: INR {format_inr(outbound['price'])}",
        TEXT
    )

    # ONE WAY → LEFT ONLY
    if intent["trip_type"] == "one_way":
        story.append(boxed_table([[outbound_cell]], [520]))

    # ROUND TRIP → TWO COLUMNS
    else:
        return_cell = Paragraph(
            "<b>Return Flight</b><br/>"
            f"{return_flight['flight_id']} ({return_flight['airline']})<br/>"
            f"{return_flight['from']} → {return_flight['to']}<br/>"
            f"Departure: {end_date.strftime('%d %b %Y')}<br/>"
            f"Arrival: {end_date.strftime('%d %b %Y')}<br/>"
            f"Duration: {return_flight['duration']}<br/>"
            f"Price: INR {format_inr(return_flight['price'])}",
            TEXT
        )

        story.append(boxed_table([[outbound_cell, return_cell]], [260, 260]))


    # HOTEL

    story.append(Paragraph("Hotel", SECTION))

    hotel = plan["HOTEL"]

    story.append(
        boxed_table(
            [
                [
                    Paragraph(f"<b>Hotel</b><br/>{hotel['name']}", TEXT),
                    Paragraph(f"<b>Stars</b><br/>{'★' * int(hotel['stars'])}", TEXT),
                    Paragraph(f"<b>Price / Night</b><br/>INR {format_inr(hotel['price_per_night'])}", TEXT),
                ],
                [
                    Paragraph(f"<b>Location</b><br/>{hotel['city']}", TEXT),
                    Paragraph(f"<b>Hotel ID</b><br/>{hotel['hotel_id']}", TEXT),
                    Paragraph(f"<b>Amenities</b><br/>{', '.join(hotel.get('amenities', []))}", TEXT),
                ]
            ],
            [170, 170, 170]
        )
    )

    
    # WEATHER

    story.append(Paragraph("Weather Forecast", SECTION))

    weather_rows = []
    
    for d in plan["WEATHER"]["daily_forecast"]:
        weather_rows.append([
            Paragraph(
                f"{d['date']} → {d['condition']}% | "
                f"({d['temp_min']}°C – {d['temp_max']}°C)% |  "
                f"Rain Probability: {d['rain_probability']}% | "
                f"Comfort Index: {d['comfort_index']}/100",
                TEXT
            )
        ])
    story.append(boxed_table(weather_rows, [520]))


    # BUDGET SUMMARY

    story.append(Paragraph("Budget Summary", SECTION))

    travelers = intent["travelers"]
    nights = max(intent["days"] - 1, 1)

    budget = plan["BUDGET_ESTIMATE"]["breakdown"]
    total = plan["BUDGET_ESTIMATE"]["total_estimated_cost"]

    budget_rows = [
        [
            Paragraph(
                "<b>Flight</b><br/>"
                f"Round-trip: {intent['source']} → {intent['destination']} → {intent['source']}",
                TEXT
            ),
            Paragraph(
                f"<b>INR {format_inr(budget['flight'])}</b><br/>"
                f"INR {format_inr(budget['flight']//travelers)} / person",
                TEXT
            )
        ],
        [
            Paragraph(
                "<b>Hotel</b><br/>"
                f"{travelers} travelers × {nights} nights",
                TEXT
            ),
            Paragraph(
                f"<b>INR {format_inr(budget['hotel'])}</b><br/>"
                f"INR {format_inr(budget['hotel']//travelers)} / person",
                TEXT
            )
        ],
        [
            Paragraph(
                "<b>Food + Local Travel + Miscellaneous</b><br/>"
                f"{travelers} travelers × {intent['days']} days",
                TEXT
            ),
            Paragraph(
                f"<b>INR {format_inr(budget['food_local_travel'])}</b><br/>"
                f"INR {format_inr(budget['food_local_travel']//travelers)} / person",
                TEXT
            )
        ],
        [
            Paragraph("<b>TOTAL ESTIMATED COST</b>", BOLD),
            Paragraph(
                f"<b>INR {format_inr(total)}</b><br/>"
                f"INR {format_inr(total//travelers)} / person",
                BOLD
            )
        ]
    ]

    story.append(boxed_table(budget_rows, [320, 200]))
    

    # NEW PAGE — DAY WISE ITINERARY

    story.append(PageBreak())
    story.append(Paragraph("Day-Wise Itinerary", SECTION))

    itinerary_rows = []

    for day in plan["DAY_WISE_ITINERARY"]:
        itinerary_rows.append([
            Paragraph(
                f"<b>{day['day']} – {day['date']}</b><br/>{day['plan']}",
                TEXT
            )
        ])

    story.append(boxed_table(itinerary_rows, [520]))
    
    

    # BUILD PDF

    doc.build(story)
