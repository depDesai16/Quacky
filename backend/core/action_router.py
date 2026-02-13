# backend/core/action_router.py
import re
from backend.weather.weather_commands import maybe_handle_weather_action
from backend.holidays.holiday_helper import maybe_handle_holiday_action
from backend.tools import open_app

def maybe_handle_direct_action(message: str) -> str | None:
    """
    Run deterministic app actions for high-confidence commands (non-calendar).
    Returns a tool-result string or None if not handled.
    """
    raw_text = (message or "").strip()
    text = raw_text.lower()

    holiday_result = maybe_handle_holiday_action(raw_text)
    if holiday_result is not None:
        return holiday_result

    weather_result = maybe_handle_weather_action(raw_text)
    if weather_result is not None:
        return weather_result

    app_match = re.match(r"^(open|launch|start)\s+(.+?)\s*$", text, flags=re.IGNORECASE)
    if app_match:
        return open_app(app_match.group(2))

    return None
