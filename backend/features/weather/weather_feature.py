# backend/weather_feature.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.weatherapi.com/v1"

MAX_FORECAST_DAYS = 7

class WeatherAPIError(Exception):
    pass

def _get_key() -> str:
    key = os.getenv("WEATHERAPI_KEY")
    if not key:
        raise WeatherAPIError("Missing WEATHERAPI_KEY in .env")
    return key

def _request(endpoint: str, params: dict) -> dict:
    """Shared request helper with consistent error handling."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        raise WeatherAPIError(f"WeatherAPI request failed: {e}") from e

    if r.status_code != 200:
        raise WeatherAPIError(f"WeatherAPI error {r.status_code}: {r.text}")

    try:
        return r.json()
    except ValueError as e:
        raise WeatherAPIError("WeatherAPI returned non-JSON response") from e


def _normalize_days(days: int) -> int:
    """Clamp days to the allowed 1–MAX_FORECAST_DAYS range."""
    if days < 1:
        return 1
    if days > MAX_FORECAST_DAYS:
        return MAX_FORECAST_DAYS
    return days

def _normalize_query(q: str | None) -> str:
    """
    WeatherAPI 'q' supports: city name, zip/postal, lat/long, 'auto:ip', etc.
    If empty/None, fall back to auto:ip (IP-based geolocation).
    """
    q = (q or "").strip()
    return q if q else "auto:ip"

def get_current_weather(query: str = "") -> dict:
    """
    Current conditions for a given location query (city/zip/lat,long).
    Omit query or pass "" to auto-detect via IP.
    """
    params = {"key": _get_key(), "q": _normalize_query(query), "aqi": "no"}
    return _request("current.json", params)


def get_forecast(query: str = "", days: int = 3) -> dict:
    """
    Forecast for a given location query (city/zip/lat,long).
    Omit query or pass "" to auto-detect via IP.
    Days are capped at MAX_FORECAST_DAYS.
    """
    days = _normalize_days(days)
    params = {
        "key": _get_key(),
        "q": _normalize_query(query),
        "days": days,
        "aqi": "no",
        "alerts": "no",
    }
    return _request("forecast.json", params)

def get_current_weather_auto_ip() -> dict:
    return get_current_weather("auto:ip")

def get_forecast_auto_ip(days: int = 3) -> dict:
    return get_forecast("auto:ip", days=days)

def _build_place_label(loc: dict) -> str:
    name = (loc.get("name") or "").strip()
    region = (loc.get("region") or "").strip()
    country = (loc.get("country") or "").strip()
    return ", ".join([p for p in [name, region] if p]) or country or "Current location"


def format_current(data: dict) -> str:
    loc = data.get("location", {})
    cur = data.get("current", {})

    place = _build_place_label(loc)

    cond = (cur.get("condition") or {}).get("text", "Unknown conditions")
    temp_f = cur.get("temp_f")
    feels_f = cur.get("feelslike_f")
    wind_mph = cur.get("wind_mph")
    humidity = cur.get("humidity")

    parts = [f"{place}: {cond}"]

    if temp_f is not None:
        if feels_f is not None:
            parts.append(f"{temp_f}°F (feels {feels_f}°F)")
        else:
            parts.append(f"{temp_f}°F")

    if wind_mph is not None:
        parts.append(f"wind {wind_mph} mph")

    if humidity is not None:
        parts.append(f"humidity {humidity}%")

    return ", ".join(parts) + "."


def format_forecast_days(data: dict, start_index: int, count: int) -> str:
    """
    Formats a slice of forecast days from WeatherAPI's forecast response.
    start_index=0 => today, 1 => tomorrow, etc.
    count is silently capped at MAX_FORECAST_DAYS.
    """
    loc = data.get("location", {})
    forecast = (data.get("forecast") or {}).get("forecastday", [])

    place = _build_place_label(loc)

    if not isinstance(forecast, list) or not forecast:
        return f"{place} forecast: (no forecast data available)"

    start_index = max(0, start_index)
    count = max(1, min(count, MAX_FORECAST_DAYS))

    days = forecast[start_index: start_index + count]

    lines = [f"{place} forecast:"]
    for d in days:
        date_label = d.get("date", "Unknown date")
        day = d.get("day", {})
        cond = (day.get("condition") or {}).get("text", "Unknown conditions")
        hi = day.get("maxtemp_f")
        lo = day.get("mintemp_f")
        rain = day.get("daily_chance_of_rain")
        rain_part = f", rain chance {rain}%" if rain is not None else ""

        if hi is not None and lo is not None:
            lines.append(f"- {date_label}: {cond}, high {hi}°F / low {lo}°F{rain_part}")
        elif hi is not None:
            lines.append(f"- {date_label}: {cond}, high {hi}°F{rain_part}")
        elif lo is not None:
            lines.append(f"- {date_label}: {cond}, low {lo}°F{rain_part}")
        else:
            lines.append(f"- {date_label}: {cond}{rain_part}")

    return "\n".join(lines)


def get_weekend_forecast(query: str = "") -> str:
    """
    Fetches Saturday and Sunday forecast for the coming weekend.
    Defaults to IP-based location when query is empty.
    Capped at MAX_FORECAST_DAYS from today.
    """
    from datetime import date

    today = date.today()
    weekday = today.weekday()  

    if weekday == 5:      
        days_to_sat, days_to_sun = 0, 1
    elif weekday == 6:    
        days_to_sat, days_to_sun = 6, 0   
    else:
        days_to_sat = 5 - weekday
        days_to_sun = 6 - weekday

    days_needed = min(days_to_sun + 1, MAX_FORECAST_DAYS)

    data = get_forecast(query, days=days_needed)
    forecast = (data.get("forecast") or {}).get("forecastday", [])

    loc = data.get("location", {})
    place = _build_place_label(loc)

    weekend_days = []
    for d in forecast:
        try:
            d_date = date.fromisoformat(d.get("date", ""))
            if d_date.weekday() in (5, 6):
                weekend_days.append(d)
        except Exception:
            continue

    if not weekend_days:
        return f"{place} forecast: (no weekend data available within {MAX_FORECAST_DAYS} days)"

    lines = [f"{place} weekend forecast:"]
    for d in weekend_days:
        day_data = d.get("day", {})
        cond = (day_data.get("condition") or {}).get("text", "Unknown conditions")
        hi = day_data.get("maxtemp_f")
        lo = day_data.get("mintemp_f")
        rain = day_data.get("daily_chance_of_rain")
        rain_part = f", rain chance {rain}%" if rain is not None else ""
        label = d.get("date", "Unknown")
        if hi is not None and lo is not None:
            lines.append(f"- {label}: {cond}, high {hi}°F / low {lo}°F{rain_part}")
        else:
            lines.append(f"- {label}: {cond}{rain_part}")

    return "\n".join(lines)

def get_weekend_forecast_auto_ip() -> str:
    return get_weekend_forecast("")