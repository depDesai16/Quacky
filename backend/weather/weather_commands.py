# backend/weather_commands.py
import re
from backend.tools import (
    get_weather_now,
    get_weather_today,
    get_weather_tomorrow,
    get_weather_week,
    get_weather_forecast, 
    get_weather_weekend,   
)

_WEATHER_TRIGGER = re.compile(
    r"\b(weather|forecast|temperature|temp|rain|snow|wind|windy|humid|humidity|uv|heat|cold)\b",
    re.IGNORECASE,
)

_TOMORROW = re.compile(r"\b(tomorrow|tmrw|next day)\b", re.IGNORECASE)
_TODAY = re.compile(r"\b(today)\b", re.IGNORECASE)
_NOW = re.compile(r"\b(now|right now|currently|current)\b", re.IGNORECASE)

_WEEK = re.compile(
    r"\b(week|weekly|7\s*day|seven\s*day|this week|next week)\b",
    re.IGNORECASE,
)

_WEEKEND = re.compile(r"\b(weekend|this weekend|next weekend)\b", re.IGNORECASE)

_DAYS_COUNT = re.compile(
    r"\b(?:next\s*)?(\d{1,2})\s*(?:day|days)\b|\b(\d{1,2})\s*-\s*day\b",
    re.IGNORECASE,
)

def _extract_days(text: str) -> int | None:
    m = _DAYS_COUNT.search(text)
    if not m:
        return None
    raw = m.group(1) or m.group(2)
    try:
        n = int(raw)
    except Exception:
        return None
    if n < 1:
        n = 1
    if n > 10:
        n = 10
    return n

def maybe_handle_weather_action(raw_text: str) -> str | None:
    """
    Returns RAW weather tool output for clear weather requests.
    Styling is handled elsewhere.
    """
    text = (raw_text or "").strip()
    if not text:
        return None

    if not _WEATHER_TRIGGER.search(text):
        return None

    if _NOW.search(text):
        return get_weather_now()

    if _TOMORROW.search(text):
        return get_weather_tomorrow()

    if _WEEKEND.search(text):
        return get_weather_weekend()

    if _WEEK.search(text):
        return get_weather_week()

    days = _extract_days(text)
    if days is not None:
        return get_weather_forecast(days=days)

    if _TODAY.search(text):
        return get_weather_today()

    return get_weather_today()
