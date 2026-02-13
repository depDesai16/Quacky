# backend/calendar/calendar_commands.py
"""
Parse natural-language calendar commands into structured action dicts.

Handles a wide variety of phrasings, e.g.:
  CREATE
    "add a meeting tomorrow at 2pm called Dentist for 30 minutes"
    "schedule Backend Refactor Test tomorrow 2pm for 30 minutes"
    "create event called Standup on Friday at 9am for 1 hour"
    "set up a 1-hour meeting next Monday at 10am named Sprint Planning"
    "put Team Lunch on my calendar for Wednesday at noon"
    "book Dentist appointment for tomorrow 3pm, 45 minutes"

  UPDATE
    "move Dentist to Friday 3pm"
    "reschedule Sprint Planning to next Monday at 10am for 1 hour"
    "change the Standup meeting to tomorrow 9am"
    "update 'Team Lunch' to Wednesday at noon"

  DELETE
    "cancel Dentist"
    "remove the Team Lunch event"
    "delete Sprint Planning meeting"
"""

import re
from datetime import date, datetime, time, timedelta

def _parse_duration_minutes(duration_text: str) -> int | None:
    """
    Convert a human-readable duration string to integer minutes.

    Handles: "30 minutes", "1 hour", "1.5 hours", "90m", "2h", "half hour",
             "an hour", "1 hour 30 minutes", "1h30m", "1:30", etc.
    Returns None when no duration can be detected.
    """
    text = (duration_text or "").strip().lower()
    if not text:
        return None

    if re.search(r"\bhalf\s+(?:an\s+)?hour\b", text):
        return 30

    if re.match(r"^an?\s+hour$", text):
        return 60

    colon = re.match(r"^(\d+):([0-5]\d)$", text)
    if colon:
        return int(colon.group(1)) * 60 + int(colon.group(2))

    compact = re.match(r"^(\d+)h(?:(\d+)m)?$", text)
    if compact:
        return int(compact.group(1)) * 60 + int(compact.group(2) or 0)
    compact_m = re.match(r"^(\d+)m$", text)
    if compact_m:
        return int(compact_m.group(1))

    decimal = re.search(r"(\d+(?:\.\d+)?)\s*[-\s]?hours?", text)
    if decimal:
        return int(float(decimal.group(1)) * 60)

    hours = 0
    minutes = 0

    hour_match = re.search(r"(\d+)\s*[-\s]?(?:hours?|hrs?)", text)
    if hour_match:
        hours = int(hour_match.group(1))
        if re.search(r"\band\s+(?:a\s+)?half\b", text):
            minutes += 30

    minute_match = re.search(r"(\d+)\s*[-\s]?(?:minutes?|mins?)", text)
    if minute_match:
        minutes += int(minute_match.group(1))

    if hours == 0 and minutes == 0:
        bare = re.match(r"^(\d+)$", text)
        if bare:
            return int(bare.group(1))
        return None

    return hours * 60 + minutes

_CREATE_VERBS = r"(?:add|create|schedule|set\s+up|book|put|make|plan|new)"
_UPDATE_VERBS = r"(?:update|move|reschedule|change|shift|edit|push|bump)"
_DELETE_VERBS = r"(?:delete|remove|cancel|drop|clear|kill)"

_AT_ON = r"(?:at\s+|on\s+|for\s+)?"

_TITLE = r'["\']?(?P<title>.+?)["\']?'

_DUR_CLAUSE = r"(?:\s+for\s+(?P<duration>[^,]+?))?"

_EVENT_NOUNS = {"meeting", "appointment", "call", "event", "standup", "sync", "session", "conference", "workshop", "seminar"}

def _clean_title(title: str) -> str:
    """Strip trailing or leading event-type nouns and connector words from a raw title."""
    t = title.strip().strip("\"'").strip()
    t = re.sub(
        r"\s+(?:meeting|appointment|call|event|standup|sync|session|conference|workshop|seminar)$",
        "", t, flags=re.IGNORECASE
    ).strip()
    t = re.sub(r"^(?:a|an|the)\s+", "", t, flags=re.IGNORECASE)
    return t


def _build_action(op: str, title: str, strip_event_noun: bool = False, **kwargs) -> dict:
    title = title.strip().strip("\"'").strip()
    if strip_event_noun:
        title = _clean_title(title)
    return {"kind": "calendar", "op": op, "title": title, **kwargs}


def _extract_duration_from_title(title: str) -> tuple[str, int]:
    """
    If the title string contains an embedded 'for N minutes/hours' clause,
    strip it out and return (clean_title, duration_minutes).
    Otherwise return (title, 0).
    """
    m = re.search(r"\s+for\s+(.+)$", title, flags=re.IGNORECASE)
    if m:
        dur = _parse_duration_minutes(m.group(1))
        if dur:
            return title[: m.start()].strip(), dur
    return title, 0

def _try_create(raw: str) -> dict | None:
    """Try every known CREATE pattern; return action dict or None."""
    r = raw.strip()

    m = re.match(
        r"^" + _CREATE_VERBS + r"\s+"
        r"(?:a\s+|an\s+|the\s+)?"
        r"(?:(?P<embedded_dur>(?:half(?:\s+an?)?\s+hour|\d+(?:[-.]\d+)?\s*[-\s]?(?:hour|hr|minute|min)s?))\s+)?"
        r"(?:(?:calendar\s+)?(?:event|meeting|appointment|call|standup|sync|session|workshop|seminar|conference|webinar)\s+)?"
        r"(?P<start>.+?)\s+for\s+(?P<duration>.+?)\s+"
        r"(?:called|named|titled)\s+(?P<title>.+?)\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        start_time = m.group("start").strip()
        dur = _parse_duration_minutes(m.group("duration")) or _parse_duration_minutes(m.group("embedded_dur") or "") or 0
        title = m.group("title").strip().strip("\"'")
        if dur and dur > 0 and title:
            return _build_action(
                "create", title,
                args={"title": title, "start_time": start_time, "duration_minutes": dur},
                summary=f"create event '{title}' at {start_time} for {dur} minutes",
            )

    _DATE_ANCHOR = (
        r"(?:today|tomorrow|tonight|this\s+\w+|next\s+\w+|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"mon|tue|wed|thu|fri|sat|sun|"
        r"\d{1,2}[/-]\d{1,2}|\d{4}-\d{2}-\d{2})"
    )
    m = re.match(
        r"^" + _CREATE_VERBS + r"\s+"
        r"(?:a\s+|an\s+|the\s+)?"
        r"(?:(?P<embedded_dur>(?:half(?:\s+an?)?\s+hour|\d+(?:[-.]\d+)?\s*[-\s]?(?:hour|hr|minute|min)s?))\s+)?"
        r"(?:(?:calendar\s+)?(?:event|meeting|appointment|call|standup|sync|session)\s+)?"
        r"(?:called|named|titled)\s+"
        r"(?P<title>.+?)\s+"
        r"(?=(?:on\s+)?(?:at\s+)?" + _DATE_ANCHOR + r")"
        r"(?:on\s+|at\s+|@\s*)?"
        r"(?P<start>.+?)"
        r"(?:\s+for\s+(?P<duration>.+?))?\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip().strip("\"'")
        start_time = m.group("start").strip()
        dur = (_parse_duration_minutes(m.group("duration") or "")
               or _parse_duration_minutes(m.group("embedded_dur") or "")
               or 0)
        if title and start_time:
            return _build_action(
                "create", title,
                args={"title": title, "start_time": start_time, "duration_minutes": dur or 60},
                summary=f"create event '{title}' at {start_time}"
                        + (f" for {dur} minutes" if dur else ""),
            )

    m = re.match(
        r"^" + _CREATE_VERBS + r"\s+"
        r"(?:a\s+|an\s+)?"
        r"(?P<duration>(?:half(?:\s+an?)?\s+hour|\d+(?:[-.]\d+)?\s*[-\s]?(?:hour|hr|minute|min)s?))?\s*"
        r"(?:(?:calendar\s+)?(?:event|meeting|appointment|call|standup|sync|session|workshop|seminar|conference|webinar))\s+"
        r"(?P<start>.+?)\s+"
        r"(?:called|named|titled)\s+(?P<title>.+?)"
        r"(?:\s+for\s+(?P<duration2>.+?))?\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        dur = _parse_duration_minutes(m.group("duration") or "") or _parse_duration_minutes(m.group("duration2") or "") or 0
        title = m.group("title").strip().strip("\"'")
        start_time = m.group("start").strip()
        if title and start_time:
            return _build_action(
                "create", title,
                args={"title": title, "start_time": start_time, "duration_minutes": dur or 60},
                summary=f"create event '{title}' at {start_time}"
                        + (f" for {dur} minutes" if dur else ""),
            )

    m = re.match(
        r"^" + _CREATE_VERBS + r"\s+"
        r"(?:a\s+|an\s+|the\s+)?"
        r"(?:(?:calendar\s+)?(?:event|meeting|appointment|call|standup|sync|session)\s+)?"
        r"(?:(?:called|named|titled)\s+)?"
        r'(?P<title>.+?)\s+'
        r"(?:on\s+|at\s+|@\s*)?"
        r"(?P<start>(?:today|tomorrow|tonight|this\s+\w+|next\s+\w+|(?:mon|tue|wed|thu|fri|sat|sun)\w*"
        r"|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{4}-\d{2}-\d{2})"
        r"(?:\s+(?:at\s+)?(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight))?)"
        r"(?:\s+for\s+(?P<duration>.+?))?\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip().strip("\"'")
        title = re.sub(r"^(?:a|an|the)\s+", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s+on\s+(?:my\s+|the\s+)?calendar$", "", title, flags=re.IGNORECASE).strip()
        title = re.sub(r"\s+for$", "", title, flags=re.IGNORECASE).strip()
        start_time = m.group("start").strip()
        dur = _parse_duration_minutes(m.group("duration") or "") or 0
        if title and len(title) > 1 and title.lower() not in {"meeting", "appointment", "call", "event", "standup", "sync", "session"}:
            return _build_action(
                "create", title,
                args={"title": title, "start_time": start_time, "duration_minutes": dur or 60},
                summary=f"create event '{title}' at {start_time}"
                        + (f" for {dur} minutes" if dur else ""),
            )

    m = re.match(
        r"^" + _CREATE_VERBS + r"\s+"
        r"(?:a\s+|an\s+|the\s+)?"
        r"(?:(?:calendar\s+)?(?:event|meeting|appointment|call|standup|sync|session)\s+)?"
        r"(?P<title>.+?)\s+"
        r"(?:on\s+(?:my\s+calendar\s+)?|at\s+|@\s*|for\s+)"
        r"(?P<start>(?:today|tomorrow|tonight|this\s+\w+|next\s+\w+|(?:mon|tue|wed|thu|fri|sat|sun)\w*"
        r"|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        r"|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{4}-\d{2}-\d{2})"
        r"(?:\s+(?:at\s+)?(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight))?)\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip().strip("\"'")
        title = re.sub(r"^(?:a|an|the)\s+", "", title, flags=re.IGNORECASE)
        start_time = m.group("start").strip()
        if title and len(title) > 1 and start_time:
            return _build_action(
                "create", title,
                args={"title": title, "start_time": start_time, "duration_minutes": 60},
                summary=f"create event '{title}' at {start_time}",
            )

    return None

def _try_update(raw: str) -> dict | None:
    r = raw.strip()

    _DATE_ANCHOR = (
        r"(?:today|tomorrow|tonight|this\s+\w+|next\s+\w+|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"mon|tue|wed|thu|fri|sat|sun|"
        r"\d{1,2}[/-]\d{1,2}|\d{4}-\d{2}-\d{2}|\d{1,2}(?::\d{2})?\s*(?:am|pm))"
    )

    m = re.match(
        r"^" + _UPDATE_VERBS + r"\s+"
        r"(?:the\s+|my\s+)?"
        r"(?P<title>.+?)\s+"
        r"(?:to|from)\s+"
        r"(?P<new_start>.+?)"
        r"(?:\s+for\s+(?P<duration>.+?))?\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip().strip("\"'")
        new_start = m.group("new_start").strip()
        dur_text = (m.group("duration") or "").strip()
        new_dur = _parse_duration_minutes(dur_text) if dur_text else 0
        if title and new_start:
            _GENERIC_EVENT_WORDS = {"meeting", "call", "event", "sync", "session", "conference", "standup"}
            parts = title.split()
            if len(parts) >= 2 and parts[-1].lower() in _GENERIC_EVENT_WORDS:
                second_last = parts[-2].lower() if len(parts) >= 2 else ""
                if second_last in _GENERIC_EVENT_WORDS or len(parts) == 2:
                    title = " ".join(parts[:-1]).strip()
            return _build_action(
                "update", title,
                args={
                    "title": title,
                    "new_start_time": new_start,
                    "new_duration_minutes": new_dur or 0,
                },
                summary=f"update event '{title}' to {new_start}"
                        + (f" for {new_dur} minutes" if new_dur else ""),
            )

    return None

def _try_delete(raw: str) -> dict | None:
    r = raw.strip()

    m = re.match(
        r"^" + _DELETE_VERBS + r"\s+"
        r"(?:the\s+|my\s+)?"
        r'(?P<title>["\']?.+?["\']?)'
        r"(?:\s+(?:from\s+(?:my\s+)?(?:calendar|schedule)))?\.?\s*$",
        r, flags=re.IGNORECASE,
    )
    if m:
        title = m.group("title").strip().strip("\"'")
        _GENERIC_ONLY = {"meeting", "call", "event", "sync", "session", "conference", "standup"}
        parts = title.split()
        if len(parts) >= 2 and parts[-1].lower() in _GENERIC_ONLY:
            title = " ".join(parts[:-1]).strip()
        if title:
            return _build_action(
                "delete", title,
                args={"title": title},
                summary=f"delete event '{title}'",
            )

    return None

def parse_calendar_action(raw_text: str) -> dict | None:
    """
    Try to parse *raw_text* as a calendar command.

    Returns a dict with keys:
        kind      → "calendar"
        op        → "create" | "update" | "delete"
        title     → cleaned event title (str)
        args      → kwargs to pass to the feature function
        summary   → human-readable summary for confirmation prompt
    Returns None if the text doesn't look like a calendar command.
    """
    text = (raw_text or "").strip()
    if not text:
        return None

    lower = text.lower()

    if re.match(r"^(?:add|create|schedule|set\s+up|book|put|make|plan|new)\b", lower):
        result = _try_create(text)
        if result:
            return result

    if re.match(r"^(?:update|move|reschedule|change|shift|edit|push|bump)\b", lower):
        result = _try_update(text)
        if result:
            return result

    if re.match(r"^(?:delete|remove|cancel|drop|clear|kill)\b", lower):
        result = _try_delete(text)
        if result:
            return result

    return None