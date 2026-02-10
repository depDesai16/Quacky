import json
import os
from urllib import response
import uuid
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from backend.tools import (
    get_calendar_events, send_email, open_app,
    get_weather_today, get_weather_tomorrow, get_weather_week
)


if load_dotenv:
    load_dotenv()


MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "8000"))

if not API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")

client = genai.Client(api_key=API_KEY)

_TOOLS = [
    get_calendar_events,
    send_email,
    open_app,
    get_weather_today,
    get_weather_tomorrow,
    get_weather_week,
]

_TOPIC_KEYWORDS = {
    "weather": ["weather", "forecast", "temperature", "temp", "rain", "snow", "wind", "umbrella"],
    "calendar": ["calendar", "events", "schedule", "appointment", "meeting"],
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
- Calendar/events: offer to add an event or set a reminder.
- Email: offer to draft the email or open Outlook.
- Tasks/reminders: offer to set a reminder with a suggested time.

If the user already asked for the extended info (e.g., “tomorrow”, “week”, “add event”, “draft email”), do not ask a follow-up.
Keep follow-ups to one sentence.
"""


_CHATS: dict[str, object] = {}
_MEMORY: dict[str, dict] = {}


def _create_chat(system_instruction: str | None = None, model: str | None = None):
    merged_system = (system_instruction or "").strip()
    if merged_system:
        merged_system += "\n\n" + FOLLOWUP_POLICY
    else:
        merged_system = FOLLOWUP_POLICY

    chat = client.chats.create(
        model=model or MODEL_NAME,
        config=types.GenerateContentConfig(
            system_instruction=merged_system,
            tools=_TOOLS,
            temperature=0.2,
        ),
    )
    return chat

def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))

def _detect_topic(text: str) -> str | None:
    t = text.lower()
    for topic, words in _TOPIC_KEYWORDS.items():
        if any(w in t for w in words):
            return topic
    return None

def _is_ambiguous_followup(text: str) -> bool:
    t = text.strip().lower()
    return any(t.startswith(p) for p in _FOLLOWUP_PREFIXES)

def _augment_with_context(chat_id: str, message: str) -> str:
    mem = _MEMORY.get(chat_id, {})
    last_topic = mem.get("last_topic")

    if _detect_topic(message):
        return message

    if last_topic and _is_ambiguous_followup(message):
        if last_topic == "weather":
            return f"Regarding the weather, {message}"
        if last_topic == "calendar":
            return f"Regarding my calendar, {message}"
        if last_topic == "email":
            return f"Regarding email, {message}"
        if last_topic == "app":
            return f"Regarding opening apps, {message}"

    return message

def _update_memory(chat_id: str, user_message: str):
    topic = _detect_topic(user_message)
    if topic:
        _MEMORY.setdefault(chat_id, {})["last_topic"] = topic

class QuackyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return

        if self.path.startswith("/chat/history"):
            _, _, query = self.path.partition("?")
            params = dict(pair.split("=", 1) for pair in query.split("&") if "=" in pair)
            chat_id = params.get("chat_id")
            if not chat_id or chat_id not in _CHATS:
                _json_response(self, 404, {"error": "chat not found"})
                return
            chat = _CHATS[chat_id]
            history = []
            for message in chat.get_history():
                text = "".join(part.text for part in message.parts if getattr(part, "text", None))
                history.append({"role": message.role, "text": text})
            _json_response(self, 200, {"chat_id": chat_id, "history": history})
            return

        _json_response(self, 404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/chat/start":
            data = _read_json(self)
            system_instruction = data.get("system")
            model = data.get("model")
            chat_id = str(uuid.uuid4())
            _CHATS[chat_id] = _create_chat(system_instruction=system_instruction, model=model)
            _MEMORY[chat_id] = {}
            _json_response(self, 200, {"chat_id": chat_id, "model": model or MODEL_NAME})
            return

        if self.path == "/chat/message":
            data = _read_json(self)
            chat_id = data.get("chat_id")
            message = data.get("message")

            if not chat_id or chat_id not in _CHATS:
                _json_response(self, 404, {"error": "chat not found"})
                return

            if not message:
                _json_response(self, 400, {"error": "message is required"})
                return

            chat = _CHATS[chat_id]

            augmented = _augment_with_context(chat_id, message)
            _update_memory(chat_id, message)

            try:
                response = chat.send_message(augmented)
                _json_response(self, 200, {
                    "chat_id": chat_id,
                    "text": response.text
                })

            except genai_errors.ClientError as e:
                msg = str(e)

                if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                    _json_response(self, 429, {
                        "error": (
                            "Gemini free-tier quota exceeded. "
                            "Please wait and try again, or enable billing for higher limits."
                        )
                    })
                else:
                    _json_response(self, 500, {"error": msg})

            return

        if self.path == "/chat/reset":
            data = _read_json(self)
            chat_id = data.get("chat_id")
            if not chat_id or chat_id not in _CHATS:
                _json_response(self, 404, {"error": "chat not found"})
                return
            del _CHATS[chat_id]
            _MEMORY.pop(chat_id, None)
            _json_response(self, 200, {"status": "reset"})
            return

        _json_response(self, 404, {"error": "not found"})


def run_server():
    server = ThreadingHTTPServer(("", PORT), QuackyHandler)
    print(f"Quacky server listening on http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
