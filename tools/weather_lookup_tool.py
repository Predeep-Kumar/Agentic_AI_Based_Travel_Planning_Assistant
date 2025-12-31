from typing import Dict, Any, List
from datetime import datetime, date, timedelta
import requests

# CONFIGURATION


MAX_FORECAST_DAYS = 10  # Open-Meteo reliable window
CACHE_TTL_DAYS = 1      # Refresh cache daily



# CITY COORDINATES


CITY_COORDINATES = {
    "delhi": {"lat": 28.6139, "lon": 77.2090},
    "goa": {"lat": 15.2993, "lon": 74.1240},
    "bangalore": {"lat": 12.9716, "lon": 77.5946},
    "mumbai": {"lat": 19.0760, "lon": 72.8777},
    "kolkata": {"lat": 22.5726, "lon": 88.3639},
}


# WEATHER CODE MAP


WEATHER_CODE_MAP = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Cloudy",
    45: "Fog",
    48: "Dense Fog",
    51: "Light Drizzle",
    61: "Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    80: "Rain Showers",
    95: "Thunderstorm",
}


# ===============================
# IN-MEMORY CACHE (AGENT MEMORY)
# ===============================

_WEATHER_CACHE: Dict[str, Dict[str, Any]] = {}


# ===============================
# HELPERS
# ===============================

def _weather_summary(code: int) -> str:
    return WEATHER_CODE_MAP.get(code, "Variable Weather")


def _rain_probability(code: int) -> int:
    if code in (61, 63, 65, 80):
        return 70
    if code in (51,):
        return 40
    if code in (95,):
        return 85
    return 10


def _risk_score(temp_max: float, rain_prob: int) -> int:
    score = 0

    if temp_max >= 38:
        score += 35
    elif temp_max >= 33:
        score += 20
    elif temp_max <= 10:
        score += 25

    score += int(rain_prob * 0.5)

    return min(score, 100)


def _comfort_index(temp_max: float, rain_prob: int) -> int:
    comfort = 100
    comfort -= abs(temp_max - 28) * 2
    comfort -= rain_prob * 0.4
    return max(int(comfort), 0)


def _confidence_level(days_ahead: int) -> str:
    if days_ahead <= 3:
        return "Very High"
    if days_ahead <= 7:
        return "High"
    if days_ahead <= 10:
        return "Medium"
    return "Low"


def _seasonal_outlook(city: str) -> str:
    return "Dry and pleasant winter weather" if city.lower() == "goa" else "Seasonal average conditions"


# ===============================
# MAIN WEATHER TOOL
# ===============================

def weather_lookup(
    city: str,
    start_date: str,
    end_date: str,
    return_date: str | None = None
) -> Dict[str, Any]:

    if not city:
        raise ValueError("City is required")

    city_key = city.lower()
    if city_key not in CITY_COORDINATES:
        raise ValueError(f"Weather not supported for city: {city}")

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    today = date.today()
    days_ahead = (start - today).days

    cache_key = f"{city_key}:{start}:{end}"
    cached = _WEATHER_CACHE.get(cache_key)

    # ---------------- CACHE HIT ----------------
    if cached:
        age = (today - cached["cached_on"]).days
        if age <= CACHE_TTL_DAYS:
            return cached["data"]

    # ---------------- FAR FUTURE (SEASONAL MODE) ----------------
    if days_ahead > MAX_FORECAST_DAYS:
        data = {
            "city": city.title(),
            "start_date": start_date,
            "end_date": end_date,
            "summary": "Detailed forecast not available yet",
            "seasonal_outlook": _seasonal_outlook(city),
            "confidence": _confidence_level(days_ahead),
            "weather_risk_score": 25,
            "rain_probability_avg": 15,
            "best_day_to_travel": start_date,
            "note": "Forecast will auto-refresh closer to travel date",
            "daily_forecast": [],
        }

        _WEATHER_CACHE[cache_key] = {
            "cached_on": today,
            "data": data
        }

        return data

    # ---------------- API CALL ----------------
    coords = CITY_COORDINATES[city_key]
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "daily": "temperature_2m_max,temperature_2m_min,weathercode",
        "timezone": "auto",
        "start_date": start_date,
        "end_date": end_date,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    daily = data["daily"]
    forecast = []

    best_day = None
    best_comfort = -1
    total_risk = 0
    total_rain = 0

    for i, day in enumerate(daily["time"]):
        temp_max = daily["temperature_2m_max"][i]
        temp_min = daily["temperature_2m_min"][i]
        code = daily["weathercode"][i]

        condition = _weather_summary(code)
        rain_prob = _rain_probability(code)
        risk = _risk_score(temp_max, rain_prob)
        comfort = _comfort_index(temp_max, rain_prob)

        total_risk += risk
        total_rain += rain_prob

        if comfort > best_comfort:
            best_comfort = comfort
            best_day = day

        forecast.append({
            "date": day,
            "temp_max": temp_max,
            "temp_min": temp_min,
            "condition": condition,
            "rain_probability": rain_prob,
            "risk_score": risk,
            "comfort_index": comfort,
        })

    data = {
        "city": city.title(),
        "start_date": start_date,
        "end_date": end_date,
        "summary": "Weather forecast available",
        "confidence": _confidence_level(days_ahead),
        "weather_risk_score": int(total_risk / len(forecast)),
        "rain_probability_avg": int(total_rain / len(forecast)),
        "best_day_to_travel": best_day,
        "daily_forecast": forecast,
    }

    _WEATHER_CACHE[cache_key] = {
        "cached_on": today,
        "data": data
    }

    return data
