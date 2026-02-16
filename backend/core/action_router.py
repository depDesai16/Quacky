# backend/core/action_router.py
"""
Intent dispatcher for Quacky.

Receives classified intents from intent_classifier.py and routes
weather, holiday, and open_app to their handlers.

Calendar intents are NOT handled here - they go through the
confirmation flow in chat_runtime.py.
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
            result = get_weather(timeframe)
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