import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_LOCK = threading.Lock()
_FILE = Path(__file__).resolve().parents[1] / "data" / "local_settings.json"
_GOOGLE_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _ensure_parent() -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(_FILE.parent, 0o700)
    except OSError:
        pass


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
    tmp_file = _FILE.with_suffix(f"{_FILE.suffix}.tmp")
    tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp_file, _FILE)
    try:
        os.chmod(_FILE, 0o600)
    except OSError:
        pass


def get_api_key() -> str:
    with _LOCK:
        data = _read_data()
        value = data.get("gemini_api_key", "")
        return str(value).strip() if value is not None else ""


def has_api_key() -> bool:
    return bool(get_api_key())


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


def get_screen_viewing_enabled(default: bool = False) -> bool:
    with _LOCK:
        data = _read_data()
        raw = data.get("screen_viewing_enabled", default)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(raw)


def save_screen_viewing_enabled(enabled: bool) -> None:
    with _LOCK:
        data = _read_data()
        data["screen_viewing_enabled"] = bool(enabled)
        _write_data(data)


def get_allowed_app_targets(default: list[str] | None = None) -> list[str]:
    with _LOCK:
        data = _read_data()
        raw = data.get("allowed_app_targets")
        if raw is None:
            return list(default or [])
        if not isinstance(raw, list):
            return list(default or [])

        allowed: list[str] = []
        seen: set[str] = set()
        for item in raw:
            value = str(item or "").strip()
            lowered = value.lower()
            if not value or lowered in seen:
                continue
            seen.add(lowered)
            allowed.append(value)
        return allowed


def save_allowed_app_targets(targets: list[str]) -> None:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in targets or []:
        value = str(item or "").strip()
        lowered = value.lower()
        if not value or lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(value)

    with _LOCK:
        data = _read_data()
        data["allowed_app_targets"] = cleaned
        _write_data(data)


def get_app_control_suggestions_enabled(default: bool = False) -> bool:
    with _LOCK:
        data = _read_data()
        raw = data.get("app_control_suggestions_enabled", default)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(raw)


def save_app_control_suggestions_enabled(enabled: bool) -> None:
    with _LOCK:
        data = _read_data()
        data["app_control_suggestions_enabled"] = bool(enabled)
        _write_data(data)


def test_api_key(api_key: str) -> tuple[bool, str]:
    key = api_key.strip()
    if not key:
        return False, "Enter an API key first."

    url = _GOOGLE_MODELS_URL + "?" + urllib.parse.urlencode({"key": key})
    req = urllib.request.Request(url, method="GET")
    try:
        # This endpoint is fixed to Google's https API host.
        with urllib.request.urlopen(req, timeout=8) as resp:  # nosec B310
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
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False, f"Key test failed (HTTP {exc.code})."
        return False, f"Key test failed (HTTP {exc.code})."
    except Exception as exc:
        return False, f"Key test failed: {exc}"
