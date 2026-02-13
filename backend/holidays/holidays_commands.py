import re
from backend.holidays.holidays_feature import get_upcoming_us_holidays

_TRIGGER = re.compile(r"\b(holiday|holidays)\b", re.IGNORECASE)

def maybe_handle_holiday_action(raw_text: str) -> str | None:
    text = (raw_text or "").strip()

    if not text:
        return None

    if not _TRIGGER.search(text):
        return None

    return get_upcoming_us_holidays(limit=10)
