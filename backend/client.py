import json
import os
import socket
import urllib.error
import urllib.request


class QuackyClient:
    """Minimal HTTP client for Quacky server endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Configure base URL and request timeout."""
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = int(os.getenv("QUACKY_CLIENT_TIMEOUT", "180"))

    def _post(self, path: str, payload: dict):
        """Send a JSON POST request and return parsed response payload."""
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
        """Send a GET request and return parsed JSON payload."""
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
        """Return server health payload."""
        return self._get("/health")

    def start_chat(self, system: str | None = None, model: str | None = None) -> dict:
        """Create a new chat session with optional system prompt and model override."""
        payload = {}
        if system:
            payload["system"] = system
        if model:
            payload["model"] = model
        return self._post("/chat/start", payload)

    def send_message(self, chat_id: str, message: str, tts: bool | None = None) -> dict:
        """Send one user message and return model response payload."""
        payload = {"chat_id": chat_id, "message": message}
        if tts is not None:
            payload["tts"] = tts
        return self._post("/chat/message", payload)

    def history(self, chat_id: str) -> dict:
        """Fetch message history for a chat id."""
        return self._get(f"/chat/history?chat_id={chat_id}")

    def reset(self, chat_id: str) -> dict:
        """Reset and delete server-side state for a chat id."""
        return self._post("/chat/reset", {"chat_id": chat_id})
