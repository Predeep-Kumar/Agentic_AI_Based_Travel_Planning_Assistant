from typing import Dict, Any, List, Optional

from utils.helpers import load_json, validate_fields


# ---------------- Configuration ---------------- #

PLACES_DATA_PATH = "data/places.json"

REQUIRED_PLACES_FIELDS = [
    "place_id",
    "name",
    "city",
    "type",
    "rating",
]


# ---------------- Main Places Search ---------------- #

def search_places(
    city: str,
    sort_by: Optional[str] = None,
    min_rating: Optional[float] = None,
    types: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Search places in a city.

    Returns:
    {
        "places": [...],
        "filters": {
            "types": [...],
            "rating_range": {"min": x, "max": y}
        }
    }
    """

    if not city:
        raise ValueError("City is required")

    places = load_json(PLACES_DATA_PATH)
    validate_fields(places, REQUIRED_PLACES_FIELDS)

    city_normalized = city.lower().strip()

    #  Base city filtering 
    base_places = [
        p for p in places
        if city_normalized in p.get("city", "").lower()
        or p.get("city", "").lower() in city_normalized
    ]

    # HARD FALLBACK 
    if not base_places:
        base_places = places.copy()

    #  Build AVAILABLE FILTER OPTIONS 
    available_types = sorted(
        {p["type"].lower() for p in base_places}
    )

    ratings = [p["rating"] for p in base_places]
    rating_range = {
        "min": round(min(ratings), 1),
        "max": round(max(ratings), 1),
    }

    #  Apply filters 
    filtered = base_places

    if types:
        types = [t.lower() for t in types]
        filtered = [
            p for p in filtered
            if p["type"].lower() in types
        ]

    if min_rating is not None:
        filtered = [
            p for p in filtered
            if p["rating"] >= min_rating
        ]

    #  SECOND FALLBACK 
    if not filtered:
        filtered = base_places.copy()

    # Tag top-rated places
    max_rating_val = max(p["rating"] for p in filtered)

    for p in filtered:
        p["is_top_rated"] = p["rating"] == max_rating_val

    # Sorting logic 
    if sort_by == "highest_rated":
        filtered.sort(key=lambda x: -x["rating"])

    elif sort_by == "type":
        filtered.sort(key=lambda x: x["type"])

    else:
        # Recommended 
        filtered.sort(
            key=lambda x: (-x["rating"], x["name"])
        )

    return {
        "places": filtered,
        "filters": {
            "types": available_types,
            "rating_range": rating_range
        }
    }
