from datetime import datetime, time
from typing import Dict, Any, List, Optional

from utils.helpers import load_json, validate_fields


FLIGHT_DATA_PATH = "data/flights.json"

REQUIRED_FLIGHT_FIELDS = [
    "flight_id",
    "airline",
    "from",
    "to",
    "departure_time",
    "arrival_time",
    "price",
]

DEBUG = True  # set False to disable debug output


# ---------------- Helper Functions ---------------- #

def _compute_duration_minutes(dep: str, arr: str) -> int:
    return int(
        (datetime.fromisoformat(arr) - datetime.fromisoformat(dep))
        .total_seconds() // 60
    )


def _format_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} hr {m} mins"
    if h:
        return f"{h} hr"
    return f"{m} mins"


def _format_datetime(dt_str: str) -> str:
    return datetime.fromisoformat(dt_str).strftime("%d %b %Y, %H:%M")


def _time_bucket(dep_dt: datetime) -> str:
    t = dep_dt.time()
    if time(5, 0) <= t < time(12, 0):
        return "morning"
    if time(12, 0) <= t < time(17, 0):
        return "afternoon"
    if time(17, 0) <= t < time(21, 0):
        return "evening"
    return "night"


# ---------------- Main Flight Search ---------------- #

def search_flights(
    source: str,
    destination: str,
    sort_by: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    time_of_day: Optional[str] = None,
    airlines: Optional[List[str]] = None
) -> Dict[str, Any]:

    if not source or not destination:
        raise ValueError("Source and destination are required")

    flights = load_json(FLIGHT_DATA_PATH)
    validate_fields(flights, REQUIRED_FLIGHT_FIELDS)

    enriched_direct: List[Dict[str, Any]] = []
    connecting_flights: List[Dict[str, Any]] = []

    # Route-specific weekday availability
    available_weekdays = set()

    # ---------------- DIRECT FLIGHTS ---------------- #
    for f in flights:
        if f["from"].lower() != source.lower():
            continue
        if f["to"].lower() != destination.lower():
            continue

        dep_dt = datetime.fromisoformat(f["departure_time"])
        duration_min = _compute_duration_minutes(
            f["departure_time"], f["arrival_time"]
        )

        enriched_direct.append({
            "flight_id": f["flight_id"],
            "airline": f["airline"],
            "from": f["from"],
            "to": f["to"],
            "departure_time": _format_datetime(f["departure_time"]),
            "arrival_time": _format_datetime(f["arrival_time"]),
            "departure_datetime": dep_dt,
            "price": f["price"],
            "duration": _format_duration(duration_min),
            "duration_minutes": duration_min,
            "time_of_day": _time_bucket(dep_dt),
        })

        # ✅ weekday from direct flight
        available_weekdays.add(dep_dt.strftime("%A").lower())

    # ---------------- CONNECTING FLIGHTS ---------------- #
    if DEBUG:
        print("DEBUG: Checking valid connecting routes")

    for leg1 in flights:
        if leg1["from"].lower() != source.lower():
            continue

        leg1_dep_dt = datetime.fromisoformat(leg1["departure_time"])
        leg1_arr_dt = datetime.fromisoformat(leg1["arrival_time"])

        for leg2 in flights:
            if leg1["to"].lower() != leg2["from"].lower():
                continue
            if leg2["to"].lower() != destination.lower():
                continue

            if DEBUG:
                print(
                    f"Possible chain: {leg1['from']} → {leg1['to']} → {leg2['to']}"
                )

            leg2_dep_dt = datetime.fromisoformat(leg2["departure_time"])
            layover = (leg2_dep_dt - leg1_arr_dt).total_seconds() / 60

            if layover < 45:
                continue

            total_duration = (
                _compute_duration_minutes(
                    leg1["departure_time"], leg1["arrival_time"]
                )
                + _compute_duration_minutes(
                    leg2["departure_time"], leg2["arrival_time"]
                )
            )

            connecting_flights.append({
                "route": f'{leg1["from"]} → {leg1["to"]} → {leg2["to"]}',
                "total_price": leg1["price"] + leg2["price"],
                "total_duration": _format_duration(total_duration),
                "segments": [
                    {
                        "airline": leg1["airline"],
                        "from": leg1["from"],
                        "to": leg1["to"],
                        "departure_time": _format_datetime(leg1["departure_time"]),
                        "arrival_time": _format_datetime(leg1["arrival_time"]),
                        "price": leg1["price"],
                    },
                    {
                        "airline": leg2["airline"],
                        "from": leg2["from"],
                        "to": leg2["to"],
                        "departure_time": _format_datetime(leg2["departure_time"]),
                        "arrival_time": _format_datetime(leg2["arrival_time"]),
                        "price": leg2["price"],
                    },
                ],
            })

            # ✅ weekday from journey start (connecting flight)
            available_weekdays.add(leg1_dep_dt.strftime("%A").lower())

    connecting_flights.sort(key=lambda x: x["total_price"])
    connecting_flights = connecting_flights[:3]

    # ---------------- FILTER METADATA ---------------- #
    available_airlines = sorted({f["airline"] for f in enriched_direct})
    available_time_slots = sorted({f["time_of_day"] for f in enriched_direct})

    price_range = {
        "min": min((f["price"] for f in enriched_direct), default=0),
        "max": max((f["price"] for f in enriched_direct), default=0),
    }

    # ---------------- TAGS + SORT ---------------- #
    if enriched_direct:
        min_price_val = min(f["price"] for f in enriched_direct)
        min_duration = min(f["duration_minutes"] for f in enriched_direct)

        for f in enriched_direct:
            f["is_cheapest"] = f["price"] == min_price_val
            f["is_fastest"] = f["duration_minutes"] == min_duration
            f.pop("departure_datetime", None)

        enriched_direct.sort(key=lambda x: (x["time_of_day"], x["price"]))

    flight_message = None
    if not enriched_direct and connecting_flights:
        flight_message = "No direct flights available. Showing best connecting flights."
    elif not enriched_direct and not connecting_flights:
        flight_message = "No flights available for this route."

    return {
        "direct_flights": enriched_direct,
        "connecting_flights": connecting_flights,
        "available_weekdays": sorted(available_weekdays),
        "flight_message": flight_message,
        "filters": {
            "airlines": available_airlines,
            "time_of_day": available_time_slots,
            "price_range": price_range,
        },
    }
