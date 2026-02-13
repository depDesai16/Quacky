# backend/weather_commands.py
import re
from backend.tools import get_weather_today, get_weather_tomorrow, get_weather_week


_WEATHER_TRIGGER = re.compile(r"\b(weather|forecast|temperature|temp)\b", re.IGNORECASE)
_TOMORROW = re.compile(r"\b(tomorrow|next day)\b", re.IGNORECASE)
_WEEK = re.compile(r"\b(week|weekly|7\s*day|seven\s*day|this week|next week)\b", re.IGNORECASE)
_TODAY = re.compile(r"\b(today|now|right now|currently)\b", re.IGNORECASE)


def maybe_handle_weather_action(raw_text: str) -> str | None:
    """
    Returns RAW weather tool output for clear weather requests.
    Styling is handled by server.py (rephrase using system prompt).
    """
    text = (raw_text or "").strip()
    if not text:
        return None

    if not _WEATHER_TRIGGER.search(text):
        return None

    # Specific intents first
    if _TOMORROW.search(text):
        return get_weather_tomorrow()

    if _WEEK.search(text):
        return get_weather_week()

    # Default to "today" for any remaining weather trigger
    # (covers: "what's the weather?", "forecast", etc.)
    if _TODAY.search(text) or True:
        return get_weather_today()

    return None

