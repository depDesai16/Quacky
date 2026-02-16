# backend/weather_feature.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.weatherapi.com/v1"

class WeatherAPIError(Exception):
    pass

def _get_key() -> str:
    key = os.getenv("WEATHERAPI_KEY")
    if not key:
        raise WeatherAPIError("Missing WEATHERAPI_KEY in .env")
    return key

def _request(endpoint: str, params: dict) -> dict:
    """
    Shared request helper with consistent error handling.
    """
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
    if days < 1:
        return 1
    if days > 10:
        return 10
    return days


def _normalize_query(q: str | None) -> str:
    """
    WeatherAPI 'q' supports: city name, zip/postal, lat/long, 'auto:ip', etc.
    If empty/None, fall back to auto:ip.
    """
    q = (q or "").strip()
    return q if q else "auto:ip"

def get_current_weather(query: str = "") -> dict:
    """
    Current conditions for a given location query (city/zip/lat,long).
    If query is empty -> auto:ip.
    """
    params = {"key": _get_key(), "q": _normalize_query(query), "aqi": "no"}
    return _request("current.json", params)


def get_forecast(query: str = "", days: int = 3) -> dict:
    """
    Forecast for a given location query (city/zip/lat,long).
    If query is empty -> auto:ip.
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

def format_current(data: dict) -> str:
    loc = data.get("location", {})
    cur = data.get("current", {})

    name = (loc.get("name") or "").strip()
    region = (loc.get("region") or "").strip()
    country = (loc.get("country") or "").strip()

    place = ", ".join([p for p in [name, region] if p]) or country or "Current location"

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


def get_weekend_forecast_auto_ip() -> str:
    """
    Fetches Saturday and Sunday forecast regardless of what day today is.
    Calculates exact days ahead needed to reach the weekend.
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

    days_needed = days_to_sun + 1  
    if days_needed > 10:
        days_needed = 10

    data = get_forecast("auto:ip", days=days_needed)
    forecast = (data.get("forecast") or {}).get("forecastday", [])

    loc = data.get("location", {})
    name = (loc.get("name") or "").strip()
    region = (loc.get("region") or "").strip()
    place = ", ".join([p for p in [name, region] if p]) or "Forecast"

    weekend_days = []
    for d in forecast:
        try:
            from datetime import date as date_cls
            d_date = date_cls.fromisoformat(d.get("date", ""))
            if d_date.weekday() in (5, 6):  
                weekend_days.append(d)
        except Exception:
            continue

    if not weekend_days:
        return f"{place} forecast: (no weekend data available)"

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


def format_forecast_days(data: dict, start_index: int, count: int) -> str:
    """
    Formats a slice of forecast days from WeatherAPI's forecast response.
    start_index=0 => today, 1 => tomorrow, etc.
    """
    loc = data.get("location", {})
    forecast = (data.get("forecast") or {}).get("forecastday", [])

    name = (loc.get("name") or "").strip()
    region = (loc.get("region") or "").strip()
    country = (loc.get("country") or "").strip()
    place = ", ".join([p for p in [name, region] if p]) or country or "Forecast"

    if not isinstance(forecast, list) or not forecast:
        return f"{place} forecast: (no forecast data available)"

    if start_index < 0:
        start_index = 0
    if count < 1:
        count = 1

    days = forecast[start_index : start_index + count]

    lines = [f"{place} forecast:"]
    for d in days:
        date = d.get("date", "Unknown date")
        day = d.get("day", {})
        cond = (day.get("condition") or {}).get("text", "Unknown conditions")
        hi = day.get("maxtemp_f")
        lo = day.get("mintemp_f")

        rain = day.get("daily_chance_of_rain")
        rain_part = f", rain chance {rain}%" if rain is not None else ""

        if hi is not None and lo is not None:
            lines.append(f"- {date}: {cond}, high {hi}°F / low {lo}°F{rain_part}")
        elif hi is not None:
            lines.append(f"- {date}: {cond}, high {hi}°F{rain_part}")
        elif lo is not None:
            lines.append(f"- {date}: {cond}, low {lo}°F{rain_part}")
        else:
            lines.append(f"- {date}: {cond}{rain_part}")

    return "\n".join(lines)