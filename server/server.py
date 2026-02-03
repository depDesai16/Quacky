import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from tools import get_calendar_events, send_email, open_app


if load_dotenv:
    load_dotenv()


MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "8000"))

if not API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")

client = genai.Client(api_key=API_KEY)

_TOOLS = [get_calendar_events, send_email, open_app]
_CHATS: dict[str, object] = {}


def _create_chat(system_instruction: str | None = None, model: str | None = None):
    config = types.GenerateContentConfig(
        tools=_TOOLS,
        system_instruction=system_instruction,
    )
    return client.chats.create(model=model or MODEL_NAME, config=config)


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
            response = chat.send_message(message)
            _json_response(self, 200, {"chat_id": chat_id, "text": response.text})
            return

        if self.path == "/chat/reset":
            data = _read_json(self)
            chat_id = data.get("chat_id")
            if not chat_id or chat_id not in _CHATS:
                _json_response(self, 404, {"error": "chat not found"})
                return
            del _CHATS[chat_id]
            _json_response(self, 200, {"status": "reset"})
            return

        _json_response(self, 404, {"error": "not found"})


def run_server():
    server = ThreadingHTTPServer(("", PORT), QuackyHandler)
    print(f"Quacky server listening on http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
