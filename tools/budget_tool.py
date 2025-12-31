def estimate_trip_budget(
    outbound_flight,
    hotel,
    days,
    travelers,
    return_flight=None,
    budget_tier: str = "budget"
):
    """
    Estimate trip budget.
    Supports budget / mid-range / luxury tiers.
    """

    breakdown = {}

    # ---------------- Flights ---------------- #
    flight_cost = 0

    if outbound_flight:
        flight_cost += outbound_flight.get("price", 0)

    if return_flight:
        flight_cost += return_flight.get("price", 0)

    flight_cost *= travelers
    breakdown["flight"] = flight_cost

    # ---------------- Hotel ---------------- #
    hotel_cost = 0
    if hotel:
        hotel_cost = hotel.get("price_per_night", 0) * days * travelers

    breakdown["hotel"] = hotel_cost

    # ---------------- Tier-based Daily Costs ---------------- #
    tier_costs = {
        "budget": {
            "food": 400,
            "local": 250,
            "misc": 150,
        },
        "mid-range": {
            "food": 700,
            "local": 400,
            "misc": 300,
        },
        "luxury": {
            "food": 1200,
            "local": 700,
            "misc": 600,
        },
    }

    tier = tier_costs.get(budget_tier, tier_costs["budget"])

    food_cost = tier["food"] * travelers * days
    local_travel_cost = tier["local"] * travelers * days
    misc_cost = tier["misc"] * travelers * days

    food_local_travel = food_cost + local_travel_cost + misc_cost

    breakdown["food_local_travel"] = food_local_travel

    # ---------------- Total ---------------- #
    total = flight_cost + hotel_cost + food_local_travel

    return {
        "breakdown": breakdown,
        "total_estimated_cost": total,
        "currency": "INR",
        "budget_tier": budget_tier,
        "note": "Final cost may vary based on availability and season"
    }
