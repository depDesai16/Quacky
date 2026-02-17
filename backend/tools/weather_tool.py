"""
Weather tool wrapper for Quacky.
"""
from backend.features.weather.weather_feature import (
    get_current_weather_auto_ip,
    get_forecast_auto_ip,
    get_weekend_forecast_auto_ip,
    format_current,
    format_forecast_days,
)

def get_weather(timeframe: str = "today") -> str:
    """
    Get the weather forecast for the requested timeframe.

    timeframe options:
        "now"      - current conditions right now
        "today"    - today's full forecast (default)
        "tomorrow" - tomorrow's forecast
        "weekend"  - Saturday and Sunday forecast
        "week"     - 7-day forecast
        "Nd"       - N-day forecast, e.g. "3d" or "5d" (N must be 1-10)
    """
    t = (timeframe or "today").strip().lower()

    if t == "now":
        return format_current(get_current_weather_auto_ip())

    if t == "tomorrow":
        data = get_forecast_auto_ip(days=2)
        return format_forecast_days(data, start_index=1, count=1)

    if t == "weekend":
        return get_weekend_forecast_auto_ip()

    if t == "week":
        data = get_forecast_auto_ip(days=7)
        return format_forecast_days(data, start_index=0, count=7)

    if t.endswith("d") and t[:-1].isdigit():
        days = max(1, min(int(t[:-1]), 10))
        data = get_forecast_auto_ip(days=days)
        return format_forecast_days(data, start_index=0, count=days)

    data = get_forecast_auto_ip(days=1)
    return format_forecast_days(data, start_index=0, count=1)