import base64
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request


class QuackyClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = self._normalize_base_url(base_url)
        self.timeout_seconds = int(os.getenv("QUACKY_CLIENT_TIMEOUT", "180"))

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        raw = str(base_url or "").strip()
        parsed = urllib.parse.urlsplit(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must use http or https and include a host")
        return raw.rstrip("/")

    def _post(self, path: str, payload: dict):
        url = self.base_url + path
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            # The request target is constrained to a validated http(s) base URL.
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                return json.loads(body) if body else {"error": f"HTTP {exc.code}"}
            except json.JSONDecodeError:
                return {"error": f"HTTP {exc.code}: {body}"}
        except (TimeoutError, socket.timeout) as exc:
            return {"error": f"Request timed out after {self.timeout_seconds}s: {exc}"}
        except urllib.error.URLError as exc:
            return {"error": f"Request failed or timed out: {exc}"}

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        try:
            # The request target is constrained to a validated http(s) base URL.
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:  # nosec B310
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeError(f"Request timed out after {self.timeout_seconds}s: {exc}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Request failed or timed out: {exc}") from exc

    def health(self) -> dict:
        return self._get("/health")

    def start_chat(self, system: str | None = None, model: str | None = None) -> dict:
        payload = {}
        if system:
            payload["system"] = system
        if model:
            payload["model"] = model
        return self._post("/chat/start", payload)

    def send_message(
        self,
        chat_id: str,
        message: str,
        tts: bool | None = None,
        screenshot_base64: str | None = None,
        screenshot_mime_type: str | None = None,
    ) -> dict:
        payload = {"chat_id": chat_id, "message": message}
        if tts is not None:
            payload["tts"] = tts
        if screenshot_base64:
            payload["screenshot_base64"] = screenshot_base64
            payload["screenshot_mime_type"] = screenshot_mime_type or "image/png"
        return self._post("/chat/message", payload)

    def send_speech_to_speech_message(self, chat_id: str, message: str) -> dict:
        """
        Dedicated speech-to-speech call for UI wiring.
        Always requests TTS generation when available.
        """
        return self._post("/chat/speech-to-speech", {"chat_id": chat_id, "message": message})

    def get_speech_to_speech_settings(self) -> dict:
        return self._get("/settings/speech-to-speech")

    def set_speech_to_speech_enabled(self, enabled: bool) -> dict:
        return self._post("/settings/speech-to-speech", {"enabled": bool(enabled)})

    def get_open_app_confirmation_settings(self) -> dict:
        return self._get("/settings/open-app-confirmation")

    def set_open_app_confirmation_enabled(self, enabled: bool) -> dict:
        return self._post("/settings/open-app-confirmation", {"enabled": bool(enabled)})

    def get_timer_confirmation_settings(self) -> dict:
        return self._get("/settings/timer-confirmation")

    def set_timer_confirmation_enabled(self, enabled: bool) -> dict:
        return self._post("/settings/timer-confirmation", {"enabled": bool(enabled)})

    def get_screen_viewing_settings(self) -> dict:
        return self._get("/settings/screen-viewing")

    def set_screen_viewing_enabled(self, enabled: bool) -> dict:
        return self._post("/settings/screen-viewing", {"enabled": bool(enabled)})

    def get_app_control_settings(self) -> dict:
        return self._get("/settings/app-control")

    def set_app_control_settings(
        self,
        allowed_targets: list[str],
        suggest_updates_enabled: bool | None = None,
    ) -> dict:
        payload = {"allowed_targets": list(allowed_targets or [])}
        if suggest_updates_enabled is not None:
            payload["suggest_updates_enabled"] = bool(suggest_updates_enabled)
        return self._post("/settings/app-control", payload)

    def get_setup_status(self) -> dict:
        return self._get("/settings/setup-status")

    def get_memory_snapshot(self) -> dict:
        return self._get("/memory")

    def update_memory_item(self, scope: str, old_value: str, new_value: str) -> dict:
        return self._post(
            "/memory/update",
            {
                "scope": scope,
                "old_value": old_value,
                "new_value": new_value,
            },
        )

    def forget_memory_item(self, scope: str, value: str) -> dict:
        return self._post("/memory/forget", {"scope": scope, "value": value})

    def clear_memory(self, scope: str = "all") -> dict:
        return self._post("/memory/clear", {"scope": scope})

    @staticmethod
    def decode_audio_bytes(response: dict) -> bytes | None:
        """
        Decode backend `audio_base64` payload into raw bytes for playback.
        Returns None if the payload has no audio data.
        """
        b64 = response.get("audio_base64")
        if not b64:
            return None
        try:
            return base64.b64decode(b64)
        except Exception:
            return None

    def history(self, chat_id: str) -> dict:
        return self._get(f"/chat/history?chat_id={chat_id}")

    def get_timers_events_dashboard(self) -> dict:
        return self._get("/dashboard/timers-events")

    def reset(self, chat_id: str) -> dict:
        return self._post("/chat/reset", {"chat_id": chat_id})

    def get_saved_api_key(self) -> dict:
        try:
            return self._get("/settings/api-key")
        except Exception as exc:
            return {"error": str(exc)}

    def save_api_key(self, api_key: str) -> dict:
        return self._post("/settings/api-key/save", {"api_key": api_key})

    def remove_api_key(self) -> dict:
        return self._post("/settings/api-key/remove", {})

    def test_api_key(self, api_key: str | None = None) -> dict:
        payload = {}
        if api_key is not None:
            payload["api_key"] = api_key
        return self._post("/settings/api-key/test", payload)
