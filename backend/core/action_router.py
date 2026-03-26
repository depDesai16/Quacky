# backend/core/action_router.py
"""
Intent dispatcher for Quacky.

Receives classified intents from intent_classifier.py and routes
directly handled intents to their tool handlers.
"""

from backend.tools import (
    cancel_timer,
    forget_memory_item,
    get_holidays,
    get_weather,
    list_memory,
    list_timers,
    open_app,
    send_email,
    set_alarm,
    set_timer,
)


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

        elif kind == "send_email":
            result = send_email(
                email_address=intent.get("email_address", ""),
                subject=intent.get("subject", ""),
                body=intent.get("body", ""),
            )
            if result:
                results.append(result)

        elif kind == "set_timer":
            try:
                duration_seconds = int(intent.get("duration_seconds") or 0)
            except (TypeError, ValueError):
                duration_seconds = 0
            result = set_timer(
                duration_seconds=duration_seconds,
                label=intent.get("label", ""),
            )
            if result:
                results.append(result)

        elif kind == "set_alarm":
            result = set_alarm(
                alarm_time=intent.get("alarm_time", ""),
                label=intent.get("label", ""),
            )
            if result:
                results.append(result)

        elif kind == "list_timers":
            result = list_timers()
            if result:
                results.append(result)

        elif kind == "cancel_timer":
            result = cancel_timer(timer_ref=intent.get("timer_ref", ""))
            if result:
                results.append(result)

        elif kind == "list_memory":
            result = list_memory(scope=intent.get("scope", "all"))
            if result:
                results.append(result)

        elif kind == "forget_memory_item":
            result = forget_memory_item(
                scope=intent.get("scope", ""),
                value=intent.get("value", ""),
            )
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


def extract_confirmable_intent(intents: list[dict]) -> dict | None:
    """
    Return the first intent that should require explicit user confirmation.
    """
    for intent in intents:
        kind = intent.get("intent", "").lower()
        if kind in ("open_app", "send_email", "set_timer", "set_alarm", "cancel_timer", "forget_all_memory"):
            return intent
    return None


def validate_calendar_intent(intent: dict) -> str | None:
    """
    Validate a calendar intent before execution.
    Returns an error message string if validation fails, None if valid.
    """
    import re
    from datetime import datetime

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


def validate_confirmable_intent(intent: dict) -> str | None:
    """
    Validate high-impact non-calendar intents before confirmation.
    """
    kind = intent.get("intent", "").lower()

    if kind == "open_app":
        app = (intent.get("app") or "").strip()
        if not app:
            return "App name is required to open an app."
        if len(app) > 255:
            return "App name is too long (max 255 characters)."
        return None

    if kind == "send_email":
        email_address = (intent.get("email_address") or "").strip()
        subject = (intent.get("subject") or "").strip()
        body = (intent.get("body") or "").strip()

        if not email_address:
            return "Recipient email address is required."
        if "@" not in email_address or "." not in email_address.split("@")[-1]:
            return "Recipient email address looks invalid."
        if not subject:
            return "Email subject is required."
        if not body:
            return "Email body is required."
        if len(subject) > 255:
            return "Email subject is too long (max 255 characters)."
        if len(body) > 10000:
            return "Email body is too long (max 10000 characters)."

    if kind == "set_timer":
        try:
            duration = int(intent.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            duration = 0
        if duration <= 0:
            return "Timer duration must be greater than zero seconds."

    if kind == "set_alarm":
        alarm_time = (intent.get("alarm_time") or "").strip()
        if not alarm_time:
            return "Alarm time is required."

    if kind == "cancel_timer":
        timer_ref = (intent.get("timer_ref") or "").strip()
        if not timer_ref:
            return "Timer/alarm reference is required to cancel one."

    if kind == "forget_all_memory":
        scope = (intent.get("scope") or "all").strip().lower()
        if scope in {"prefs", "pref", "preference"}:
            scope = "preferences"
        elif scope in {"task", "todo", "notes"}:
            scope = "tasks"
        if scope not in {"all", "preferences", "tasks"}:
            return "Memory scope must be all, preferences, or tasks."

    return None


def build_confirmable_action(intent: dict) -> dict | None:
    """
    Convert a confirmable non-calendar intent into a pending_action payload.
    """
    kind = intent.get("intent", "").lower()

    if kind == "open_app":
        app = (intent.get("app") or "").strip()
        if not app:
            return None
        return {
            "kind": "open_app",
            "op": "open",
            "args": {"app_name": app},
            "summary": f"open '{app}'",
        }

    if kind == "send_email":
        email_address = (intent.get("email_address") or "").strip()
        subject = (intent.get("subject") or "").strip()
        body = (intent.get("body") or "").strip()
        if not (email_address and subject and body):
            return None

        body_preview = " ".join(body.split())
        if len(body_preview) > 120:
            body_preview = body_preview[:117].rstrip() + "..."

        return {
            "kind": "send_email",
            "op": "send",
            "args": {
                "email_address": email_address,
                "subject": subject,
                "body": body,
            },
            "summary": (
                f"send an email to '{email_address}' "
                f"with subject '{subject}' and body preview '{body_preview}'"
            ),
        }

    if kind == "set_timer":
        try:
            duration = int(intent.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            return None
        if duration <= 0:
            return None
        label = (intent.get("label") or "").strip()
        label_summary = f" labeled '{label}'" if label else ""
        return {
            "kind": "timer",
            "op": "set_timer",
            "args": {"duration_seconds": duration, "label": label},
            "summary": f"set a timer for {duration} seconds{label_summary}",
        }

    if kind == "set_alarm":
        alarm_time = (intent.get("alarm_time") or "").strip()
        if not alarm_time:
            return None
        label = (intent.get("label") or "").strip()
        label_summary = f" labeled '{label}'" if label else ""
        return {
            "kind": "timer",
            "op": "set_alarm",
            "args": {"alarm_time": alarm_time, "label": label},
            "summary": f"set an alarm for '{alarm_time}'{label_summary}",
        }

    if kind == "cancel_timer":
        timer_ref = (intent.get("timer_ref") or "").strip()
        if not timer_ref:
            return None
        return {
            "kind": "timer",
            "op": "cancel",
            "args": {"timer_ref": timer_ref},
            "summary": f"cancel timer/alarm '{timer_ref}'",
        }

    if kind == "forget_all_memory":
        scope = (intent.get("scope") or "all").strip().lower()
        if scope in {"prefs", "pref", "preference"}:
            scope = "preferences"
        elif scope in {"task", "todo", "notes"}:
            scope = "tasks"
        if scope not in {"all", "preferences", "tasks"}:
            scope = "all"

        scope_summary = {
            "all": "all remembered preferences and task notes",
            "preferences": "all remembered preferences",
            "tasks": "all remembered task notes",
        }[scope]
        return {
            "kind": "memory",
            "op": "clear_all",
            "args": {"scope": scope},
            "summary": f"forget {scope_summary}",
        }

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
