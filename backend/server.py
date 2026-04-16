# backend/server.py
import base64
import ipaddress
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.config import get_settings
from backend.core.activity_store import list_calendar_events
from backend.core.chat_runtime import ChatRuntime
from backend.core.runtime_logging import configure_runtime_logging, install_exception_logging
from backend.core.settings_service import (
    get_api_key as get_saved_api_key,
)
from backend.core.settings_service import (
    get_open_app_confirmation_enabled,
    get_screen_viewing_enabled,
    get_timer_confirmation_enabled,
    remove_api_key,
    save_api_key,
    save_open_app_confirmation_enabled,
    save_screen_viewing_enabled,
    save_timer_confirmation_enabled,
    test_api_key,
)
from backend.core.settings_service import (
    has_api_key as has_saved_api_key,
)
from backend.features.timers import get_active_timers_data
from backend.interact.speech_to_text.elevenlabs_wrapper import ElevenLabsTTS

settings = get_settings()
LOGGER = logging.getLogger(__name__)
LOG_PATH = configure_runtime_logging("backend")
install_exception_logging(LOGGER)

runtime = ChatRuntime(
    api_key=settings.api_key,
    model_name=settings.model_name,
)

MODEL_NAME = settings.model_name
PORT = settings.port
tts_client = (
    ElevenLabsTTS(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
        model_id=settings.elevenlabs_model_id,
    )
    if settings.elevenlabs_api_key
    else None
)
speech_to_speech_state = {"enabled": bool(settings.tts_default_enabled)}
open_app_confirmation_state = {
    "enabled": bool(get_open_app_confirmation_enabled(default=True))
}
runtime.set_open_app_confirmation_enabled(open_app_confirmation_state["enabled"])
timer_confirmation_state = {
    "enabled": bool(get_timer_confirmation_enabled(default=True))
}
runtime.set_timer_confirmation_enabled(timer_confirmation_state["enabled"])
screen_viewing_state = {
    "enabled": bool(get_screen_viewing_enabled(default=False))
}
runtime.set_screen_viewing_enabled(screen_viewing_state["enabled"])
_MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)

def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    try:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
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


def _build_chat_response(chat_id: str, text: str, tts_requested: bool) -> dict:
    payload = {"chat_id": chat_id, "text": text, "tts_requested": bool(tts_requested)}
    if tts_requested:
        if tts_client is None:
            payload["tts_error"] = "TTS unavailable: missing ELEVENLABS_API_KEY"
        else:
            try:
                audio_bytes = tts_client.synthesize(text)
                payload["audio_base64"] = base64.b64encode(audio_bytes).decode("ascii")
                payload["audio_mime_type"] = "audio/mpeg"
            except Exception as tts_exc:
                payload["tts_error"] = str(tts_exc)
    return payload


def _decode_optional_screenshot(data: dict) -> tuple[bytes | None, str | None, str | None]:
    raw = data.get("screenshot_base64")
    if raw in {None, ""}:
        return None, None, None

    try:
        decoded = base64.b64decode(str(raw), validate=True)
    except Exception:
        return None, None, "screenshot_base64 is invalid"

    if not decoded:
        return None, None, "screenshot_base64 is empty"

    if len(decoded) > _MAX_SCREENSHOT_BYTES:
        return None, None, "screenshot is too large"

    mime_type = str(data.get("screenshot_mime_type", "image/png")).strip() or "image/png"
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        mime_type = "image/png"

    return decoded, mime_type, None


def _is_loopback_client(handler: BaseHTTPRequestHandler) -> bool:
    host = handler.client_address[0]
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"

class QuackyHandler(BaseHTTPRequestHandler):
    server_version = "Quacky"
    sys_version = ""

    def log_message(self, format: str, *args) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def do_GET(self):
        if not _is_loopback_client(self):
            _json_response(self, 403, {"error": "local requests only"})
            return

        if self.path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return

        if self.path == "/settings/api-key":
            _json_response(self, 200, {"has_key": has_saved_api_key()})
            return

        if self.path == "/settings/speech-to-speech":
            _json_response(
                self,
                200,
                {
                    "enabled": bool(speech_to_speech_state["enabled"]),
                    "tts_available": bool(tts_client),
                    "default_enabled": bool(settings.tts_default_enabled),
                },
            )
            return

        if self.path == "/settings/open-app-confirmation":
            _json_response(
                self,
                200,
                {"enabled": bool(open_app_confirmation_state["enabled"])},
            )
            return

        if self.path == "/settings/timer-confirmation":
            _json_response(
                self,
                200,
                {"enabled": bool(timer_confirmation_state["enabled"])},
            )
            return

        if self.path == "/settings/screen-viewing":
            _json_response(
                self,
                200,
                {"enabled": bool(screen_viewing_state["enabled"])},
            )
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

        if self.path == "/dashboard/timers-events":
            _json_response(
                self,
                200,
                {
                    "timers": get_active_timers_data(),
                    "events": list_calendar_events(limit=40),
                },
            )
            return

        _json_response(self, 404, {"error": "not found"})


    def do_POST(self):
        if not _is_loopback_client(self):
            _json_response(self, 403, {"error": "local requests only"})
            return

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
            tts_requested = _as_bool(data.get("tts"), default=speech_to_speech_state["enabled"])
            screenshot_bytes, screenshot_mime_type, screenshot_error = _decode_optional_screenshot(data)

            if not chat_id:
                _json_response(self, 400, {"error": "chat_id is required"})
                return

            if not message:
                _json_response(self, 400, {"error": "message is required"})
                return

            if screenshot_error is not None:
                _json_response(self, 400, {"error": screenshot_error})
                return

            try:
                text = runtime.handle_message(
                    chat_id,
                    message,
                    screenshot_bytes=screenshot_bytes,
                    screenshot_mime_type=screenshot_mime_type or "image/png",
                )
                payload = _build_chat_response(chat_id, text, tts_requested)
                _json_response(self, 200, payload)
            except KeyError:
                _json_response(self, 404, {"error": "chat not found"})
            except Exception:
                LOGGER.exception("Unhandled error while processing /chat/message")
                _json_response(self, 500, {"error": "internal server error"})
            return

        if self.path == "/chat/speech-to-speech":
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
                payload = _build_chat_response(chat_id, text, True)
                _json_response(self, 200, payload)
            except KeyError:
                _json_response(self, 404, {"error": "chat not found"})
            except Exception:
                LOGGER.exception("Unhandled error while processing /chat/speech-to-speech")
                _json_response(self, 500, {"error": "internal server error"})
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

        if self.path == "/settings/api-key/save":
            data = _read_json(self)
            key = str(data.get("api_key", "")).strip()
            if not key:
                _json_response(self, 400, {"error": "api_key is required"})
                return
            save_api_key(key)
            _json_response(self, 200, {"status": "saved", "has_key": True})
            return

        if self.path == "/settings/api-key/remove":
            remove_api_key()
            _json_response(self, 200, {"status": "removed", "has_key": False})
            return

        if self.path == "/settings/api-key/test":
            data = _read_json(self)
            key = str(data.get("api_key", "")).strip() or get_saved_api_key()
            ok, message = test_api_key(key)
            _json_response(self, 200, {"ok": ok, "message": message})
            return

        if self.path == "/settings/speech-to-speech":
            data = _read_json(self)
            if "enabled" not in data:
                _json_response(self, 400, {"error": "enabled is required"})
                return
            speech_to_speech_state["enabled"] = _as_bool(data.get("enabled"), default=False)
            _json_response(
                self,
                200,
                {
                    "enabled": bool(speech_to_speech_state["enabled"]),
                    "tts_available": bool(tts_client),
                },
            )
            return

        if self.path == "/settings/open-app-confirmation":
            data = _read_json(self)
            if "enabled" not in data:
                _json_response(self, 400, {"error": "enabled is required"})
                return

            enabled = _as_bool(data.get("enabled"), default=True)
            open_app_confirmation_state["enabled"] = enabled
            runtime.set_open_app_confirmation_enabled(enabled)
            save_open_app_confirmation_enabled(enabled)
            _json_response(self, 200, {"enabled": bool(enabled)})
            return

        if self.path == "/settings/timer-confirmation":
            data = _read_json(self)
            if "enabled" not in data:
                _json_response(self, 400, {"error": "enabled is required"})
                return

            enabled = _as_bool(data.get("enabled"), default=True)
            timer_confirmation_state["enabled"] = enabled
            runtime.set_timer_confirmation_enabled(enabled)
            save_timer_confirmation_enabled(enabled)
            _json_response(self, 200, {"enabled": bool(enabled)})
            return

        if self.path == "/settings/screen-viewing":
            data = _read_json(self)
            if "enabled" not in data:
                _json_response(self, 400, {"error": "enabled is required"})
                return

            enabled = _as_bool(data.get("enabled"), default=False)
            screen_viewing_state["enabled"] = enabled
            runtime.set_screen_viewing_enabled(enabled)
            save_screen_viewing_enabled(enabled)
            _json_response(self, 200, {"enabled": bool(enabled)})
            return

        _json_response(self, 404, {"error": "not found"})

def run_server():
    LOGGER.info("Starting backend server on 127.0.0.1:%s", PORT)
    LOGGER.info("Runtime log file: %s", LOG_PATH)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), QuackyHandler)
    print(f"Quacky server listening on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt, shutting down backend server")
        print("\nShutting down server.")
    finally:
        server.server_close()
        LOGGER.info("Backend server stopped")


if __name__ == "__main__":
    run_server()
