# backend/server.py
import json
import os
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from backend.personality.init import (
    merge_system_instruction,
    augment_with_context,
    update_memory,
)
from backend.calendar.calendar_commands import parse_calendar_action
from backend.weather.weather_commands import maybe_handle_weather_action
from backend.holidays.holidays_commands import maybe_handle_holiday_action

from backend.tools import (
    add_outlook_event,
    open_app,
    send_email,
    get_weather_today,
    get_weather_tomorrow,
    get_weather_week,
    update_outlook_event_time,
    delete_outlook_event_by_title,
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
    add_outlook_event,
    open_app,
    send_email,
    get_weather_today,
    get_weather_tomorrow,
    get_weather_week,
    update_outlook_event_time,
    delete_outlook_event_by_title,
]

_CHATS: dict[str, object] = {}
_MEMORY: dict[str, dict] = {}


def _style_direct_output(chat, user_message: str, tool_result: str) -> str:
    """
    Rephrase deterministic/tool output using the same chat (and therefore the system prompt).
    This does NOT re-run tools; it only rewrites the output.
    """
    prompt = (
        "Rewrite the following tool result in Quacky's voice using the system instructions.\n"
        "Keep the factual details exactly the same.\n"
        "Be concise.\n\n"
        f"User asked: {user_message}\n\n"
        f"Tool result:\n{tool_result}"
    )
    response = chat.send_message(prompt)
    return response.text


def _is_yes(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"yes", "y", "yeah", "yep", "ok", "okay", "confirm", "sure", "go ahead", "do it", "please"}


def _is_no(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"no", "n", "nope", "nah", "cancel", "stop", "don't", "do not", "nevermind", "never mind"}


def _ask_quacky_confirmation(chat, user_message: str, action_summary: str) -> str:
    prompt = (
        "Ask the user to confirm the calendar action below in Quacky's voice using the system instructions.\n"
        "Be short, playful, and clear.\n"
        "End with a direct yes/no question.\n\n"
        f"User said: {user_message}\n"
        f"Action: {action_summary}\n"
    )
    return chat.send_message(prompt).text


def _create_chat(system_instruction: str | None = None, model: str | None = None):
    merged_system = merge_system_instruction(system_instruction)

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
    try:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
        return


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def _maybe_handle_direct_action(message: str) -> str | None:
    """Run deterministic app actions for high-confidence commands (non-calendar)."""
    raw_text = (message or "").strip()
    text = raw_text.lower()

    holiday_result = maybe_handle_holiday_action(raw_text)
    if holiday_result is not None:
        return holiday_result
    
    weather_result = maybe_handle_weather_action(raw_text)
    if weather_result is not None:
        return weather_result

    app_match = re.match(r"^(open|launch|start)\s+(.+?)\s*$", text, flags=re.IGNORECASE)
    if app_match:
        return open_app(app_match.group(2))

    return None


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
            for msg in chat.get_history():
                text = "".join(part.text for part in msg.parts if getattr(part, "text", None))
                history.append({"role": msg.role, "text": text})

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

            pending = _MEMORY.get(chat_id, {}).get("pending_action")
            if pending and pending.get("kind") == "calendar":
                original_user_message = pending.get("user_message", "")

                if _is_yes(message):
                    op = pending["op"]
                    args = pending["args"]

                    if op == "create":
                        result = add_outlook_event(**args)
                    elif op == "update":
                        result = update_outlook_event_time(**args)
                    elif op == "delete":
                        result = delete_outlook_event_by_title(**args)
                    else:
                        result = "Unknown calendar operation."

                    _MEMORY[chat_id].pop("pending_action", None)
                    update_memory(_MEMORY, chat_id, original_user_message or message)

                    try:
                        styled = _style_direct_output(chat, original_user_message or message, result)
                    except genai_errors.ClientError:
                        styled = result

                    _json_response(self, 200, {"chat_id": chat_id, "text": styled})
                    return

                if _is_no(message):
                    _MEMORY[chat_id].pop("pending_action", None)
                    update_memory(_MEMORY, chat_id, original_user_message or message)

                    cancel_text = chat.send_message(
                        "User declined the pending calendar action. Reply in Quacky's voice, short and friendly."
                    ).text
                    _json_response(self, 200, {"chat_id": chat_id, "text": cancel_text})
                    return

                clarify = chat.send_message(
                    "There is a pending calendar action awaiting confirmation. Ask the user to reply yes or no, in Quacky's voice."
                ).text
                _json_response(self, 200, {"chat_id": chat_id, "text": clarify})
                return

            calendar_action = parse_calendar_action(message)
            if calendar_action is not None:
                calendar_action["user_message"] = message  
                _MEMORY[chat_id]["pending_action"] = calendar_action
                update_memory(_MEMORY, chat_id, message)

                confirm_text = _ask_quacky_confirmation(chat, message, calendar_action["summary"])
                _json_response(self, 200, {"chat_id": chat_id, "text": confirm_text})
                return

            direct_result = _maybe_handle_direct_action(message)
            if direct_result is not None:
                update_memory(_MEMORY, chat_id, message)
                try:
                    styled = _style_direct_output(chat, message, direct_result)
                except genai_errors.ClientError:
                    styled = direct_result

                _json_response(self, 200, {"chat_id": chat_id, "text": styled})
                return

            augmented = augment_with_context(_MEMORY, chat_id, message)
            update_memory(_MEMORY, chat_id, message)

            try:
                response = chat.send_message(augmented)
                _json_response(self, 200, {"chat_id": chat_id, "text": response.text})
            except genai_errors.ClientError as e:
                msg = str(e)
                if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                    _json_response(
                        self,
                        429,
                        {
                            "error": (
                                "Gemini free-tier quota exceeded. "
                                "Please wait and try again, or enable billing for higher limits."
                            )
                        },
                    )
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
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
