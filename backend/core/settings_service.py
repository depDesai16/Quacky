import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


_LOCK = threading.Lock()
_FILE = Path(__file__).resolve().parents[1] / "data" / "local_settings.json"


def _ensure_parent() -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)


def _read_data() -> dict:
    _ensure_parent()
    if not _FILE.exists():
        return {}
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_data(data: dict) -> None:
    _ensure_parent()
    _FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_api_key() -> str:
    with _LOCK:
        data = _read_data()
        value = data.get("gemini_api_key", "")
        return str(value).strip() if value is not None else ""


def save_api_key(api_key: str) -> None:
    key = api_key.strip()
    with _LOCK:
        data = _read_data()
        data["gemini_api_key"] = key
        _write_data(data)


def remove_api_key() -> None:
    with _LOCK:
        data = _read_data()
        data.pop("gemini_api_key", None)
        _write_data(data)


def get_open_app_confirmation_enabled(default: bool = True) -> bool:
    with _LOCK:
        data = _read_data()
        raw = data.get("open_app_confirmation_enabled", default)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(raw)


def save_open_app_confirmation_enabled(enabled: bool) -> None:
    with _LOCK:
        data = _read_data()
        data["open_app_confirmation_enabled"] = bool(enabled)
        _write_data(data)


def get_timer_confirmation_enabled(default: bool = True) -> bool:
    with _LOCK:
        data = _read_data()
        raw = data.get("timer_confirmation_enabled", default)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(raw)


def save_timer_confirmation_enabled(enabled: bool) -> None:
    with _LOCK:
        data = _read_data()
        data["timer_confirmation_enabled"] = bool(enabled)
        _write_data(data)


def test_api_key(api_key: str) -> tuple[bool, str]:
    key = api_key.strip()
    if not key:
        return False, "Enter an API key first."

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models?"
        + urllib.parse.urlencode({"key": key})
    )
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8")
        payload = json.loads(body) if body else {}
        if isinstance(payload, dict) and payload.get("models"):
            return True, "API key test passed."
        return False, "Key test failed: no models returned."
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            message = payload.get("error", {}).get("message")
            if message:
                return False, f"Key test failed: {message}"
        except Exception:
            pass
        return False, f"Key test failed (HTTP {exc.code})."
    except Exception as exc:
        return False, f"Key test failed: {exc}"
