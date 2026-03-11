import json
import os
import socket
import base64
import urllib.error
import urllib.request


class QuackyClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = int(os.getenv("QUACKY_CLIENT_TIMEOUT", "180"))

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
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
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
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as resp:
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

    def send_message(self, chat_id: str, message: str, tts: bool | None = None) -> dict:
        payload = {"chat_id": chat_id, "message": message}
        if tts is not None:
            payload["tts"] = tts
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
