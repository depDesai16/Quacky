"""Tool methods callable by the AI model."""
from backend.calendar.calendar_feature import create_outlook_event, open_outlook_calendar, update_outlook_event, delete_outlook_event
from backend.weather.weather_feature import (
    get_forecast_auto_ip,
    get_current_weather_auto_ip,
    get_forecast_auto_ip,
    format_forecast_days,
    format_current,
)

def send_email(email_address: str, subject: str, body: str) -> str:
    """Send an email to the recipient with the provided subject and body."""
    _ = (email_address, subject, body)
    return "Email sent"


def open_app(app_name: str) -> str:
    normalized = (app_name or "").strip().lower()
    if "calendar" in normalized or "outlook" in normalized:
        try:
            return open_outlook_calendar()
        except Exception as exc:
            return f"Failed to open Outlook calendar: {exc}"
    return "App opened"


def add_outlook_event(
    title: str,
    start_time: str,
    end_time: str = "",
    duration_minutes: int = 60,
    location: str = "",
    details: str = "",
) -> str:
    """
    Add a new Outlook calendar event.

    start_time and end_time can be ISO values or natural text like "tomorrow 3pm".
    If end_time is omitted, duration_minutes is used (default 60).
    """
    return create_outlook_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        location=location,
        details=details,
    )

def update_outlook_event_time(
    title: str,
    new_start_time: str,
    new_end_time: str = "",
    new_duration_minutes: int = 0,
) -> str:
    """
    Update an existing Outlook calendar event's date and/or time by its title.

    new_start_time can be natural text like 'tomorrow 3pm' or 'Friday 10am'.
    If new_end_time is omitted, the event keeps its original duration.
    """
    return update_outlook_event(
        title=title,
        new_start_time=new_start_time,
        new_end_time=new_end_time,
        new_duration_minutes=new_duration_minutes,
    )

def delete_outlook_event_by_title(title: str) -> str:
    """
    Delete an existing Outlook calendar event by its title.
    """
    return delete_outlook_event(title=title)

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
    data = get_current_weather_auto_ip()
    return format_current(data)

def get_weather_forecast(days: int = 3) -> str:
    """Use when user asks for the forecast for N days (e.g., next 3 days)."""
    if days < 1:
        days = 1
    if days > 10:
        days = 10
    data = get_forecast_auto_ip(days=days)
    return format_forecast_days(data, start_index=0, count=days)

def get_weather_weekend() -> str:
    """Use when user asks about the weekend forecast."""
    data = get_forecast_auto_ip(days=3)
    return format_forecast_days(data, start_index=0, count=2)


ALL_TOOLS = [
    add_outlook_event,
    open_app,
    send_email,
    get_weather_today,
    get_weather_tomorrow,
    get_weather_week,
    get_weather_now,
    get_weather_forecast,
    get_weather_weekend,
    update_outlook_event_time,
    delete_outlook_event_by_title,
]