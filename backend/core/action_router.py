# backend/core/action_router.py
"""
Intent dispatcher for Quacky.

Receives classified intents from intent_classifier.py and routes
weather, holiday, and open_app to their handlers.
"""

from backend.tools import get_weather, get_holidays, open_app


def dispatch_intents(intents: list[dict]) -> str | None:
    """
    Dispatch all non-calendar intents and return combined results.
    Returns None if nothing was handled (caller falls through to LLM chat).
    """
    results = []

    for intent in intents:
        kind = (intent.get("intent") or "").lower()

        if kind == "weather":
            timeframe = intent.get("timeframe", "today")
            location = intent.get("location", "") 
            result = get_weather(timeframe, location)
            if result:
                results.append(result)

        elif kind == "holiday":
            result = get_holidays(
                query_type=intent.get("query_type", "upcoming"),
                date=intent.get("date", ""),
                name=intent.get("name", ""),
                month=intent.get("month", ""),
                n=intent.get("n", 5),
            )
            if result:
                results.append(result)

        elif kind == "open_app":
            app = intent.get("app", "")
            result = open_app(app)
            if result:
                results.append(result)

    return "\n\n".join(results) if results else None


def extract_calendar_intent(intents: list[dict]) -> dict | None:
    """
    Return the first calendar intent (create/update/delete) if present.
    """
    for intent in intents:
        if intent.get("intent", "").lower() in ("create_event", "update_event", "delete_event"):
            return intent
    return None


def extract_clarify_intent(intents: list[dict]) -> dict | None:
    """
    Return the first clarify intent if present.
    """
    for intent in intents:
        if intent.get("intent", "").lower() == "clarify":
            return intent
    return None


def validate_calendar_intent(intent: dict) -> str | None:
    """
    Validate a calendar intent before execution.
    Returns an error message string if validation fails, None if valid.
    """
    from datetime import datetime, timedelta
    import re

    kind = intent.get("intent", "").lower()

    if kind in ("create_event", "update_event", "delete_event"):
        title = (intent.get("title") or "").strip()
        if not title:
            return "Event title is required."
        if len(title) > 255:
            return "Event title is too long (max 255 characters)."
        if title.lower() in ("meeting", "appointment", "event", "call"):
            return "Please provide a more specific event title."

    if kind == "create_event":
        duration = int(intent.get("duration_minutes") or 60)
        if duration < 1:
            return "Event duration must be at least 1 minute."
        if duration > 480:  
            return "Event duration seems unusually long (over 8 hours). Did you mean hours instead of minutes?"

    if kind in ("create_event", "update_event"):
        time_field = "start_time" if kind == "create_event" else "new_start_time"
        time_str = (intent.get(time_field) or "").strip().lower()

        if not time_str:
            return "Event time is required."

        if any(word in time_str for word in ["yesterday", "last week", "last month", "ago"]):
            return "Cannot schedule events in the past. Did you mean a future date?"

        year_match = re.search(r'\b(202[7-9]|20[3-9]\d)\b', time_str)
        if year_match:
            year = int(year_match.group(1))
            if year > datetime.now().year + 2:
                return f"Event is scheduled for {year}, which is quite far in the future. Is that correct?"

    return None


def build_calendar_action(intent: dict) -> dict | None:
    """
    Convert a classified calendar intent into the action dict that
    confirmation.py and tools.py expect.
    Returns None if required fields are missing.
    """
    kind = intent.get("intent", "").lower()

    if kind == "create_event":
        title = (intent.get("title") or "").strip()
        start_time = (intent.get("start_time") or "").strip()
        if not title or not start_time:
            return None
        duration = int(intent.get("duration_minutes") or 60)
        return {
            "kind": "calendar",
            "op": "create",
            "title": title,
            "args": {
                "title": title,
                "start_time": start_time,
                "end_time": intent.get("end_time") or "",
                "duration_minutes": duration,
                "location": intent.get("location") or "",
                "details": intent.get("details") or "",
            },
            "summary": f"create event '{title}' at {start_time}"
                       + (f" for {duration} minutes" if duration != 60 else ""),
        }

    if kind == "update_event":
        title = (intent.get("title") or "").strip()
        new_start = (intent.get("new_start_time") or "").strip()
        if not title or not new_start:
            return None
        new_dur = int(intent.get("new_duration_minutes") or 0)
        return {
            "kind": "calendar",
            "op": "update",
            "title": title,
            "args": {
                "title": title,
                "new_start_time": new_start,
                "new_end_time": intent.get("new_end_time") or "",
                "new_duration_minutes": new_dur,
            },
            "summary": f"move '{title}' to {new_start}"
                       + (f" for {new_dur} minutes" if new_dur else ""),
        }

    if kind == "delete_event":
        title = (intent.get("title") or "").strip()
        if not title:
            return None
        return {
            "kind": "calendar",
            "op": "delete",
            "title": title,
            "args": {"title": title},
            "summary": f"delete event '{title}'",
        }

    return None