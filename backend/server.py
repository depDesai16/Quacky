# backend/server.py
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.config import get_settings
from backend.core.chat_runtime import ChatRuntime

settings = get_settings()

runtime = ChatRuntime(
    api_key=settings.api_key,
    model_name=settings.model_name,
)

MODEL_NAME = settings.model_name
PORT = settings.port

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

class QuackyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return

        if self.path.startswith("/chat/history"):
            _, _, query = self.path.partition("?")
            params = dict(pair.split("=", 1) for pair in query.split("&") if "=" in pair)
            chat_id = params.get("chat_id")

            try:
                history = runtime.get_history(chat_id)
            except KeyError:
                _json_response(self, 404, {"error": "chat not found"})
                return

            _json_response(self, 200, {"chat_id": chat_id, "history": history})
            return

        _json_response(self, 404, {"error": "not found"})


    def do_POST(self):
        if self.path == "/chat/start":
            data = _read_json(self)
            system_instruction = data.get("system")
            model = data.get("model")

            chat_id = runtime.create_chat(
                system_instruction=system_instruction,
                model=model
            )

            _json_response(
                self,
                200,
                {
                    "chat_id": chat_id,
                    "model": model or MODEL_NAME,
                },
            )
            return

        if self.path == "/chat/message":
            data = _read_json(self)
            chat_id = data.get("chat_id")
            message = data.get("message")

            if not chat_id:
                _json_response(self, 400, {"error": "chat_id is required"})
                return

            if not message:
                _json_response(self, 400, {"error": "message is required"})
                return

            try:
                text = runtime.handle_message(chat_id, message)
                _json_response(self, 200, {"chat_id": chat_id, "text": text})
            except KeyError:
                _json_response(self, 404, {"error": "chat not found"})
            except Exception as e:
                _json_response(self, 500, {"error": str(e)})
            return

        if self.path == "/chat/reset":
            data = _read_json(self)
            chat_id = data.get("chat_id")

            if not chat_id:
                _json_response(self, 400, {"error": "chat_id is required"})
                return

            try:
                runtime.reset(chat_id)
                _json_response(self, 200, {"status": "reset"})
            except KeyError:
                _json_response(self, 404, {"error": "chat not found"})
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
