"""Personality helpers and lightweight memory extraction for Quacky."""

import re

from backend.core.memory_store import (
    add_preference,
    add_task_note,
    get_preferences,
    get_task_notes,
)

_TOPIC_KEYWORDS = {
    "weather": ["weather", "forecast", "temperature", "temp", "rain", "snow", "wind", "umbrella"],
    "calendar": ["calendar", "event", "events", "schedule", "appointment", "meeting"],
    "email": ["email", "mail", "message"],
    "app": ["open", "launch", "start"],
    "tasks": ["task", "todo", "to-do", "timer", "alarm", "reminder", "remember"],
}

_FOLLOWUP_PREFIXES = (
    "what about",
    "how about",
    "and",
    "tomorrow",
    "next week",
    "this week",
    "this weekend",
    "next weekend",
    "the week",
    "next day",
    "later",
    "same",
    "same as before",
    "again",
    "that one",
    "that",
    "it",
)

_PREFERENCE_PATTERNS = (
    re.compile(r"\bi prefer (?P<value>[^.?!]+)", flags=re.IGNORECASE),
    re.compile(r"\bmy preference is (?P<value>[^.?!]+)", flags=re.IGNORECASE),
    re.compile(r"\bplease (?:always|default to) (?P<value>[^.?!]+)", flags=re.IGNORECASE),
    re.compile(
        r"\bremember that i (?:prefer|like) (?P<value>[^.?!]+)",
        flags=re.IGNORECASE,
    ),
    re.compile(r"\bcall me (?P<value>[a-zA-Z][\w \-]{0,40})", flags=re.IGNORECASE),
)

_TASK_PATTERNS = (
    re.compile(
        r"\b(?:task|todo|to-do|reminder)\s*[:\-]\s*(?P<value>[^.?!]+)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:add|create|save)\s+(?:a\s+)?(?:task|todo|to-do|reminder)\s*(?:to\s+)?(?P<value>[^.?!]+)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\badd (?:this )?to my (?:tasks|todos|to-dos|reminders)\s*(?::|-)?\s*(?P<value>[^.?!]+)",
        flags=re.IGNORECASE,
    ),
    re.compile(r"\bremember to (?P<value>[^.?!]+)", flags=re.IGNORECASE),
    re.compile(r"\bdon't let me forget to (?P<value>[^.?!]+)", flags=re.IGNORECASE),
    re.compile(r"\bmy task is to (?P<value>[^.?!]+)", flags=re.IGNORECASE),
)

_TASK_EXPLICIT_MARKERS = (
    "task",
    "todo",
    "to-do",
    "reminder",
    "remember to",
    "don't let me forget",
)

_NON_PREFERENCE_QUESTION_PREFIXES = (
    "do i ",
    "what do i ",
    "should i ",
    "would i ",
    "could i ",
)

FOLLOWUP_POLICY = """
After answering, ask at most one short follow-up question only when it helps.
Do not ask follow-ups for every message.

Ask follow-ups for these topics:
- Weather: offer tomorrow or 7-day forecast.
- Calendar/events: offer to add an event.
- Email: offer to draft the email or open Outlook.
- Tasks/reminders: offer to set a reminder with a suggested time.

If the user already asked for the extended info (e.g., "tomorrow", "week", "draft email"), do not ask a follow-up.
Keep follow-ups to one sentence.
""".strip()


def merge_system_instruction(user_system_instruction: str | None) -> str:
    """
    Merge Quacky behavior policy with any user/system prompt provided by the client.
    """
    base = (user_system_instruction or "").strip()
    if base:
        return base + "\n\n" + FOLLOWUP_POLICY
    return FOLLOWUP_POLICY


def detect_topic(text: str) -> str | None:
    t = (text or "").lower()
    for topic, words in _TOPIC_KEYWORDS.items():
        if any(w in t for w in words):
            return topic
    return None


def _is_ambiguous_followup(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t.startswith(p) for p in _FOLLOWUP_PREFIXES)


def _clean_clause(text: str) -> str:
    value = " ".join((text or "").strip().split())
    return re.sub(r"[.?!]+$", "", value).strip()


def _extract_preference(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    lower_text = text.lower()
    if "?" in text and lower_text.startswith(_NON_PREFERENCE_QUESTION_PREFIXES):
        return None
    for pattern in _PREFERENCE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = _clean_clause(match.group("value"))
        if not value:
            continue
        if pattern.pattern.startswith(r"\bcall me "):
            return f"Call me {value}"
        return value
    return None


def _extract_task_note(message: str, has_preference_match: bool = False) -> str | None:
    text = (message or "").strip()
    if not text:
        return None
    lower_text = text.lower()
    has_explicit_task_marker = any(marker in lower_text for marker in _TASK_EXPLICIT_MARKERS)
    if not has_explicit_task_marker:
        return None
    if (
        has_preference_match
        and "task" not in lower_text
        and "todo" not in lower_text
        and "reminder" not in lower_text
    ):
        return None
    for pattern in _TASK_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = _clean_clause(match.group("value"))
        if value:
            return value
    return None


def is_preference_message(message: str) -> bool:
    """Return True when the message contains a preference statement to store."""
    return _extract_preference(message) is not None


def _truncate_items(values: list[str], max_items: int, max_len: int = 90) -> list[str]:
    out: list[str] = []
    for value in values:
        v = _clean_clause(value)
        if not v:
            continue
        if len(v) > max_len:
            v = v[: max_len - 3].rstrip() + "..."
        out.append(v)
        if len(out) >= max_items:
            break
    return out


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = _clean_clause(value).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def augment_with_context(memory: dict, chat_id: str, message: str) -> str:
    """
    If user says ambiguous follow-up like "tomorrow" or "what about next week",
    rewrite it to include the last known topic so the model stays on track.
    """
    enriched = message

    if not detect_topic(message):
        last_topic = memory.get(chat_id, {}).get("last_topic")
    else:
        last_topic = None

    if last_topic and _is_ambiguous_followup(message):
        if last_topic == "weather":
            enriched = f"Regarding the weather, {message}"
        if last_topic == "calendar":
            enriched = f"Regarding calendar events, {message}"
        if last_topic == "email":
            enriched = f"Regarding email, {message}"
        if last_topic == "app":
            enriched = f"Regarding opening apps, {message}"
        if last_topic == "tasks":
            enriched = f"Regarding your tasks and reminders, {message}"

    session_tasks = list(memory.get(chat_id, {}).get("session_tasks", []) or [])
    persisted_tasks = get_task_notes(limit=4)
    persisted_prefs = get_preferences(limit=4)

    merged_tasks = _truncate_items(
        _dedupe_keep_order(session_tasks[-3:] + persisted_tasks),
        max_items=5,
    )
    merged_prefs = _truncate_items(_dedupe_keep_order(persisted_prefs), max_items=4)

    context_lines: list[str] = []
    if merged_prefs:
        context_lines.append("Known user preferences: " + "; ".join(merged_prefs))
    if merged_tasks:
        context_lines.append("Remembered user tasks/notes: " + "; ".join(merged_tasks))

    if not context_lines:
        return enriched
    return "\n".join(context_lines) + f"\n\nUser message: {enriched}"


def update_memory(memory: dict, chat_id: str, user_message: str) -> None:
    mem = memory.setdefault(chat_id, {})

    cleaned_message = _clean_clause(user_message)
    if cleaned_message:
        recents = list(mem.get("recent_user_messages", []) or [])
        recents.append(cleaned_message)
        mem["recent_user_messages"] = recents[-8:]

    topic = detect_topic(user_message)
    if topic:
        mem["last_topic"] = topic

    pref = _extract_preference(user_message)
    if pref:
        mem["last_preference"] = pref
        add_preference(pref)

    task = _extract_task_note(user_message, has_preference_match=bool(pref))
    if task:
        tasks = list(mem.get("session_tasks", []) or [])
        task_l = task.lower()
        if all(task_l != str(existing).lower() for existing in tasks):
            tasks.append(task)
        mem["session_tasks"] = tasks[-8:]
        add_task_note(task)
