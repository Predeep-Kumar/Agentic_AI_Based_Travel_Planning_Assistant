from typing import Dict, Any, List, Optional

from utils.helpers import load_json, validate_fields


# ---------------- Configuration ---------------- #

HOTEL_DATA_PATH = "data/hotels.json"

REQUIRED_HOTEL_FIELDS = [
    "hotel_id",
    "name",
    "city",
    "stars",
    "price_per_night",
    "amenities",
]


# ---------------- Main Hotel Search ---------------- #

def search_hotels(
    city: str,
    sort_by: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_stars: Optional[int] = None,
    amenities: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Search hotels in a city.

    Returns:
    {
        "hotels": [...],
        "filters": {
            "price_range": {"min": x, "max": y},
            "stars": [...],
            "amenities": [...]
        }
    }
    """

    if not city:
        raise ValueError("City is required")

    hotels = load_json(HOTEL_DATA_PATH)
    validate_fields(hotels, REQUIRED_HOTEL_FIELDS)

    city_normalized = city.lower().strip()

    #  Base city filtering (FIXED: region-aware, case-insensitive)
    base_hotels = [
        h for h in hotels
        if city_normalized in h.get("city", "").lower()
        or h.get("city", "").lower() in city_normalized
    ]

    # HARD FALLBACK (CRITICAL – real booking sites do this)
    if not base_hotels:
        base_hotels = hotels.copy()

    #  Build AVAILABLE FILTER OPTIONS (IMPORTANT)
    price_range = {
        "min": min(h["price_per_night"] for h in base_hotels),
        "max": max(h["price_per_night"] for h in base_hotels),
    }

    available_stars = sorted(
        {h["stars"] for h in base_hotels},
        reverse=True
    )

    available_amenities = sorted({
        amenity.lower()
        for h in base_hotels
        for amenity in h["amenities"]
    })

    # Apply filters (only from available options)
    filtered = base_hotels

    if min_price is not None:
        filtered = [
            h for h in filtered
            if h["price_per_night"] >= min_price
        ]

    if max_price is not None:
        filtered = [
            h for h in filtered
            if h["price_per_night"] <= max_price
        ]

    if min_stars is not None:
        filtered = [
            h for h in filtered
            if h["stars"] >= min_stars
        ]

    if amenities:
        amenities = [a.lower() for a in amenities]
        filtered = [
            h for h in filtered
            if all(
                a in [x.lower() for x in h["amenities"]]
                for a in amenities
            )
        ]

    # ✅ Second fallback (filters too strict)
    if not filtered:
        filtered = base_hotels.copy()

    # 4️⃣ Tag cheapest & best-rated (for UI badges)
    min_price_val = min(h["price_per_night"] for h in filtered)
    max_star_val = max(h["stars"] for h in filtered)

    for h in filtered:
        h["is_cheapest"] = h["price_per_night"] == min_price_val
        h["is_best_rated"] = h["stars"] == max_star_val

    # 5️⃣ Sorting logic (real booking website behavior)
    if sort_by == "price_low_to_high":
        filtered.sort(key=lambda x: x["price_per_night"])

    elif sort_by == "price_high_to_low":
        filtered.sort(key=lambda x: x["price_per_night"], reverse=True)

    elif sort_by == "highest_rated":
        filtered.sort(key=lambda x: (-x["stars"], x["price_per_night"]))

    elif sort_by == "best_value":
        # Best value = stars / price
        filtered.sort(
            key=lambda x: -(x["stars"] / x["price_per_night"])
        )

    else:
        # Recommended (default)
        filtered.sort(
            key=lambda x: (-x["stars"], x["price_per_night"])
        )

    return {
        "hotels": filtered,
        "filters": {
            "price_range": price_range,
            "stars": available_stars,
            "amenities": available_amenities
        }
    }
