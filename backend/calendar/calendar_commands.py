# backend/calendar/calendar_commands.py
import re

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
        minutes += int(minute_match.group(1))

    if hours == 0 and minutes == 0:
        single = re.search(r"^(\d+)\s*(m|h)$", text)
        if single:
            value = int(single.group(1))
            return value * 60 if single.group(2) == "h" else value
        return None

    return hours * 60 + minutes


def parse_calendar_action(raw_text: str) -> dict | None:
    """
    Returns a dict describing the intended action, without executing it.
    """
    raw_text = (raw_text or "").strip()

    m = re.match(
        r"^(?:add|create|schedule|set(?:\s+up)?)\s+(?:a\s+)?(?:calendar\s+)?(?:event|meeting|appointment)?\s*"
        r"(?P<start>.+?)\s+for\s+(?P<duration>.+?)\s+"
        r"(?:called|named|titled)\s+(?P<title>.+?)\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if m:
        dur = _parse_duration_minutes(m.group("duration"))
        if not dur or dur <= 0:
            return None
        title = m.group("title").strip()
        start_time = m.group("start").strip()
        return {
            "kind": "calendar",
            "op": "create",
            "args": {"title": title, "start_time": start_time, "duration_minutes": dur},
            "summary": f"create event '{title}' at {start_time} for {dur} minutes",
        }

    m = re.match(
        r"^(?:add|create|schedule|set(?:\s+up)?)\s+(?:a\s+)?(?:calendar\s+)?(?:event|meeting|appointment)?\s*"
        r"(?P<start>.+?)\s+"
        r"(?:called|named|titled)\s+(?P<title>.+?)\s+for\s+(?P<duration>.+?)\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if m:
        dur = _parse_duration_minutes(m.group("duration"))
        if not dur or dur <= 0:
            return None
        title = m.group("title").strip()
        start_time = m.group("start").strip()
        return {
            "kind": "calendar",
            "op": "create",
            "args": {"title": title, "start_time": start_time, "duration_minutes": dur},
            "summary": f"create event '{title}' at {start_time} for {dur} minutes",
        }

    m = re.match(
        r"^(?:update|move|reschedule|change)\s+(?:the\s+)?[\"']?(?P<title>.+?)[\"']?\s+"
        r"(?:to)\s+(?P<new_start>.+?)(?:\s+for\s+(?P<duration>.+?))?\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip()
        new_start = m.group("new_start").strip()
        dur_text = (m.group("duration") or "").strip()
        new_dur = _parse_duration_minutes(dur_text) if dur_text else 0
        return {
            "kind": "calendar",
            "op": "update",
            "args": {"title": title, "new_start_time": new_start, "new_duration_minutes": new_dur or 0},
            "summary": f"update event '{title}' to {new_start}" + (f" for {new_dur} minutes" if new_dur else ""),
        }

    m = re.match(
        r"^(?:delete|remove|cancel)\s+(?:the\s+)?[\"']?(?P<title>.+?)[\"']?\s*(?:event|meeting|appointment)?\.?\s*$",
        raw_text,
        flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip()
        return {
            "kind": "calendar",
            "op": "delete",
            "args": {"title": title},
            "summary": f"delete event '{title}'",
        }

    return None
