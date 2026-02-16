# backend/core/intent_classifier.py
"""
LLM-based intent classifier for Quacky.

Uses the same Gemini model as the main chat to classify every user message
into one or more structured intents before routing to the correct handler.

Supported intents:
    create_event   -> calendar create
    update_event   -> calendar update
    delete_event   -> calendar delete
    weather        -> weather lookup
    holiday        -> holiday lookup
    open_app       -> open an application
    chat           -> general conversation, falls through to main LLM
"""

import json
import re

from google import genai
from google.genai import types

_CLASSIFIER_SYSTEM = """
You are the intent classifier for Quacky, an unhinged but helpful desktop AI assistant.
Your ONLY job is to read the user message and return a JSON array of intents.
Output ONLY the JSON array - no explanation, no markdown, no backticks, nothing else.

AVAILABLE INTENTS

1. create_event
   Required: title (str), start_time (str - natural language ok, e.g. "Friday 2pm")
   Optional: end_time (str), duration_minutes (int, default 60), location (str), details (str)

2. update_event
   Required: title (str), new_start_time (str)
   Optional: new_end_time (str), new_duration_minutes (int)

3. delete_event
   Required: title (str)

4. weather
   Required: timeframe - one of: "now", "today", "tomorrow", "weekend", "week", or "Nd" (e.g. "3d" for 3 days)

5. holiday
   Required: query_type - one of: "upcoming", "federal", "check_date", "find", "month", "today"
   Optional:
     date  (str ISO YYYY-MM-DD) for check_date
     name  (str) for find e.g. "Thanksgiving"
     month (str) for month e.g. "July"
     n     (int) for upcoming/federal, how many to show (default 5)

6. open_app
   Required: app (str - e.g. "outlook", "spotify", "vs code", "chrome")

7. chat
   No fields. Use for casual conversation or anything that does not match above.

RULES
- Always return a JSON array, even for one intent: [{"intent": "chat"}]
- For combined questions return multiple intents in one array
- Clean calendar titles - strip generic suffixes like "meeting", "appointment", "event", "call" unless they are part of the actual name
- Keep natural language times as-is in start_time/new_start_time - do not convert to ISO
- If intent is ambiguous or required fields are missing return [{"intent": "chat"}]

EXAMPLES

"hey how are you?"
[{"intent": "chat"}]

"what's the weather like today?"
[{"intent": "weather", "timeframe": "today"}]

"will it rain this weekend?"
[{"intent": "weather", "timeframe": "weekend"}]

"give me a 5 day forecast"
[{"intent": "weather", "timeframe": "5d"}]

"any holidays coming up?"
[{"intent": "holiday", "query_type": "upcoming"}]

"next 10 holidays"
[{"intent": "holiday", "query_type": "upcoming", "n": 10}]

"when is thanksgiving?"
[{"intent": "holiday", "query_type": "find", "name": "Thanksgiving"}]

"holidays in july"
[{"intent": "holiday", "query_type": "month", "month": "July"}]

"federal holidays this month"
[{"intent": "holiday", "query_type": "federal"}]

"is july 4th a holiday?"
[{"intent": "holiday", "query_type": "check_date", "date": "2026-07-04"}]

"schedule a dentist appointment friday at 2pm for 45 minutes"
[{"intent": "create_event", "title": "Dentist", "start_time": "Friday 2pm", "duration_minutes": 45}]

"put team sync on my calendar monday at 9am"
[{"intent": "create_event", "title": "Team Sync", "start_time": "Monday 9am"}]

"I need to meet with sarah next tuesday at 3"
[{"intent": "create_event", "title": "Meeting with Sarah", "start_time": "next Tuesday 3pm"}]

"move dentist to next wednesday at 10am"
[{"intent": "update_event", "title": "Dentist", "new_start_time": "next Wednesday 10am"}]

"cancel dentist"
[{"intent": "delete_event", "title": "Dentist"}]

"remove the team sync meeting"
[{"intent": "delete_event", "title": "Team Sync"}]

"open outlook"
[{"intent": "open_app", "app": "outlook"}]

"is it going to rain on july 4th and is that a holiday?"
[{"intent": "weather", "timeframe": "today"}, {"intent": "holiday", "query_type": "check_date", "date": "2026-07-04"}]

"what's the weather this weekend and do we have any holidays coming up?"
[{"intent": "weather", "timeframe": "weekend"}, {"intent": "holiday", "query_type": "upcoming"}]
"""


def classify(message: str, client: genai.Client, model_name: str) -> list[dict]:
    """
    Classify a user message into a list of intent dicts.
    Always returns at least [{"intent": "chat"}] - never raises.
    """
    if not (message or "").strip():
        return [{"intent": "chat"}]

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=message.strip(),
            config=types.GenerateContentConfig(
                system_instruction=_CLASSIFIER_SYSTEM,
                temperature=0.0,
                max_output_tokens=512,
            ),
        )

        raw = (response.text or "").strip()

        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        intents = json.loads(raw)

        if not isinstance(intents, list):
            return [{"intent": "chat"}]

        validated = [
            item for item in intents
            if isinstance(item, dict) and "intent" in item
        ]

        return validated if validated else [{"intent": "chat"}]

    except Exception:
        return [{"intent": "chat"}]