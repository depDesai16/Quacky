# backend/calendar_commands.py
import re

from backend.tools import (
    add_outlook_event,
    update_outlook_event_time,
    delete_outlook_event_by_title,
)


def _parse_duration_minutes(duration_text: str) -> int | None:
    text = (duration_text or "").strip().lower()
    if not text:
        return None

    if "half hour" in text:
        return 30

    hours = 0
    minutes = 0

    hour_match = re.search(r"(\d+)\s*(hours?|hrs?)", text)
    if hour_match:
        hours = int(hour_match.group(1))
        if re.search(r"\band\s+(?:a\s+)?half\b", text):
            minutes += 30

    minute_match = re.search(r"(\d+)\s*(minutes?|mins?)", text)
    if minute_match:
        minutes = int(minute_match.group(1)) + (minutes if hours else 0)

    if hours == 0 and minutes == 0:
        single_match = re.search(r"^(\d+)\s*(m|h)$", text)
        if single_match:
            value = int(single_match.group(1))
            return value * 60 if single_match.group(2) == "h" else value
        return None

    return hours * 60 + minutes


def maybe_handle_calendar_action(raw_text: str) -> str | None:
    """
    Deterministic calendar commands:
      - create/add event
      - update/move event
      - delete/remove event
    """
    raw_text = (raw_text or "").strip()

    # Create event: "schedule 2pm for 30 minutes called Team Sync"
    event_match = re.match(
        r"^(?:add|create|schedule|set(?:\s+up)?)\s+(?:a\s+)?(?:calendar\s+)?(?:event|meeting|appointment)?\s*"
        r"(?P<start>.+?)\s+for\s+(?P<duration>.+?)\s+"
        r"(?:called|named|titled)\s+(?P<title>.+?)\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if event_match:
        duration_minutes = _parse_duration_minutes(event_match.group("duration"))
        if duration_minutes is None or duration_minutes <= 0:
            return None

        title = event_match.group("title").strip()
        start_time = event_match.group("start").strip()

        return add_outlook_event(
            title=title,
            start_time=start_time,
            duration_minutes=duration_minutes,
        )

    # Update event: "update 'Team Sync' to 3pm for 45 minutes"
    update_match = re.match(
        r"^(?:update|move|reschedule|change)\s+(?:the\s+)?[\"']?(?P<title>.+?)[\"']?\s+"
        r"(?:to|for)\s+(?P<new_start>.+?)(?:\s+for\s+(?P<duration>.+?))?\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if update_match:
        title = update_match.group("title").strip()
        new_start = update_match.group("new_start").strip()
        duration_text = update_match.group("duration") or ""
        new_duration = _parse_duration_minutes(duration_text) or 0

        return update_outlook_event_time(
            title=title,
            new_start_time=new_start,
            new_duration_minutes=new_duration,
        )

    # Delete event: "delete 'Team Sync'"
    delete_match = re.match(
        r"^(?:delete|remove|cancel)\s+(?:the\s+)?[\"']?(?P<title>.+?)[\"']?\s*(?:event|meeting|appointment)?\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if delete_match:
        title = delete_match.group("title").strip()
        return delete_outlook_event_by_title(title=title)

    return None
