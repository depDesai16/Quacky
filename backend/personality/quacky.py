# backend/personality/quacky.py
_TOPIC_KEYWORDS = {
    "weather": ["weather", "forecast", "temperature", "temp", "rain", "snow", "wind", "umbrella"],
    "calendar": ["calendar", "event", "events", "schedule", "appointment", "meeting"],
    "email": ["email", "mail", "message"],
    "app": ["open", "launch", "start"],
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


def augment_with_context(memory: dict, chat_id: str, message: str) -> str:
    """
    If user says ambiguous follow-up like "tomorrow" or "what about next week",
    rewrite it to include the last known topic so the model stays on track.
    """
    if detect_topic(message):
        return message

    last_topic = memory.get(chat_id, {}).get("last_topic")
    if last_topic and _is_ambiguous_followup(message):
        if last_topic == "weather":
            return f"Regarding the weather, {message}"
        if last_topic == "calendar":
            return f"Regarding calendar events, {message}"
        if last_topic == "email":
            return f"Regarding email, {message}"
        if last_topic == "app":
            return f"Regarding opening apps, {message}"

    return message


def update_memory(memory: dict, chat_id: str, user_message: str) -> None:
    topic = detect_topic(user_message)
    if topic:
        memory.setdefault(chat_id, {})["last_topic"] = topic
