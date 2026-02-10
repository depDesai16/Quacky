import json
import urllib.error
import urllib.request


class QuackyClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

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
            with urllib.request.urlopen(req) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                return json.loads(body) if body else {"error": f"HTTP {exc.code}"}
            except json.JSONDecodeError:
                return {"error": f"HTTP {exc.code}: {body}"}

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        try:
            with urllib.request.urlopen(url) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc

    def health(self) -> dict:
        return self._get("/health")

    def start_chat(self, system: str | None = None, model: str | None = None) -> dict:
        payload = {}
        if system:
            payload["system"] = system
        if model:
            payload["model"] = model
        return self._post("/chat/start", payload)

    def send_message(self, chat_id: str, message: str) -> dict:
        return self._post("/chat/message", {"chat_id": chat_id, "message": message})

    def history(self, chat_id: str) -> dict:
        return self._get(f"/chat/history?chat_id={chat_id}")

    def reset(self, chat_id: str) -> dict:
        return self._post("/chat/reset", {"chat_id": chat_id})
