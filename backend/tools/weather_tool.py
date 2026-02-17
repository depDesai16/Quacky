"""
Weather tool wrapper for Quacky.
"""
from backend.features.weather.weather_feature import (
    MAX_FORECAST_DAYS,
    get_current_weather,
    get_current_weather_auto_ip,
    get_forecast,
    get_forecast_auto_ip,
    get_weekend_forecast,
    format_current,
    format_forecast_days,
)

def get_weather(timeframe: str = "today", location: str = "") -> str:
    """
    Get the weather forecast for the requested timeframe and optional location.

    Args:
        timeframe:
            "now"      - current conditions right now
            "today"    - today's full forecast (default)
            "tomorrow" - tomorrow's forecast
            "weekend"  - Saturday and Sunday forecast
            "week"     - 7-day forecast
            "Nd"       - N-day forecast, e.g. "3d" or "5d" (N capped at 7)

        location:
            City name, zip/postal code, "lat,long", or empty string.
            When empty, location is auto-detected via IP address.

    Examples:
        get_weather("today")                  -> forecast for detected location
        get_weather("today", "New York")      -> forecast for New York
        get_weather("3d", "London")           -> 3-day forecast for London
        get_weather("now", "90210")           -> current conditions for zip 90210
    """
    t = (timeframe or "today").strip().lower()
    loc = (location or "").strip()

    if t == "now":
        data = get_current_weather(loc) if loc else get_current_weather_auto_ip()
        return format_current(data)

    if t == "tomorrow":
        data = get_forecast(loc, days=2) if loc else get_forecast_auto_ip(days=2)
        return format_forecast_days(data, start_index=1, count=1)

    if t == "weekend":
        return get_weekend_forecast(loc)

    if t == "week":
        days = MAX_FORECAST_DAYS  # 7
        data = get_forecast(loc, days=days) if loc else get_forecast_auto_ip(days=days)
        return format_forecast_days(data, start_index=0, count=days)

    if t.endswith("d") and t[:-1].isdigit():
        days = max(1, min(int(t[:-1]), MAX_FORECAST_DAYS))
        data = get_forecast(loc, days=days) if loc else get_forecast_auto_ip(days=days)
        return format_forecast_days(data, start_index=0, count=days)

    data = get_forecast(loc, days=1) if loc else get_forecast_auto_ip(days=1)
    return format_forecast_days(data, start_index=0, count=1)