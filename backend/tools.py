# Tool methods for the AI to use.
# These are intentionally stubbed; wire them into real services later.
from backend.weather_api import (
    get_current_weather_auto_ip,
    format_current,
    get_forecast_auto_ip,
    format_forecast_days,
)
from backend.openapp import open_app as open_local_app

def get_calendar_events() -> str:
    """Return a short summary of upcoming calendar events."""
    return "Calendar events"

def send_email(email_address: str, subject: str, body: str) -> str:
    """Send an email to the recipient with the provided subject and body."""
    return "Email sent"

def open_app(app_name: str) -> str:
    """Open a local application by name."""
    return open_local_app(app_name)

def get_weather_today() -> str:
    """Use when the user asks 'what's the weather' or asks for today's weather."""
    data = get_forecast_auto_ip(days=1)
    return format_forecast_days(data, start_index=0, count=1)


def get_weather_tomorrow() -> str:
    """Use when the user asks for tomorrow's weather."""
    data = get_forecast_auto_ip(days=2)  
    return format_forecast_days(data, start_index=1, count=1)


def get_weather_week() -> str:
    """Use when the user asks for the weather for the whole week / 7-day forecast."""
    data = get_forecast_auto_ip(days=7)
    return format_forecast_days(data, start_index=0, count=7)



def get_weather_now() -> str:
    """Alias for today's weather (kept for compatibility)."""
    return get_weather_today()
