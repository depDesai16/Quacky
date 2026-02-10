# backend/weather_api.py
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


def get_current_weather_auto_ip() -> dict:
    """
    Current conditions for the caller's IP-based location.
    """
    url = f"{BASE_URL}/current.json"
    params = {"key": _get_key(), "q": "auto:ip", "aqi": "no"}

    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        raise WeatherAPIError(f"WeatherAPI error {r.status_code}: {r.text}")

    return r.json()


def get_forecast_auto_ip(days: int = 3) -> dict:
    """
    Forecast for the caller's IP-based location.
    WeatherAPI supports up to 10 days depending on plan; we clamp to 1..10.
    """
    if days < 1:
        days = 1
    if days > 10:
        days = 10

    url = f"{BASE_URL}/forecast.json"
    params = {"key": _get_key(), "q": "auto:ip", "days": days, "aqi": "no", "alerts": "no"}

    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        raise WeatherAPIError(f"WeatherAPI error {r.status_code}: {r.text}")

    return r.json()


def format_current(data: dict) -> str:
    loc = data["location"]
    cur = data["current"]
    place = f'{loc["name"]}, {loc.get("region","")}'.strip().strip(",")
    cond = cur["condition"]["text"]
    return (
        f"{place}: {cond}, {cur['temp_f']}°F (feels {cur['feelslike_f']}°F), "
        f"wind {cur['wind_mph']} mph, humidity {cur['humidity']}%."
    )


def format_forecast_days(data: dict, start_index: int, count: int) -> str:
    """
    Formats a slice of forecast days from WeatherAPI's forecast response.
    start_index=0 => today, 1 => tomorrow, etc.
    """
    loc = data["location"]
    place = f'{loc["name"]}, {loc.get("region","")}'.strip().strip(",")

    all_days = data["forecast"]["forecastday"]
    days = all_days[start_index : start_index + count]

    lines = [f"{place} forecast:"]
    for d in days:
        date = d["date"]
        day = d["day"]
        cond = day["condition"]["text"]
        hi = day["maxtemp_f"]
        lo = day["mintemp_f"]
        rain = day.get("daily_chance_of_rain")
        rain_part = f", rain chance {rain}%" if rain is not None else ""
        lines.append(f"- {date}: {cond}, high {hi}°F / low {lo}°F{rain_part}")
    return "\n".join(lines)
