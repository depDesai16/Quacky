from __future__ import annotations

import difflib
import os
import re
import shlex
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
from urllib.parse import quote_plus, urlparse

from backend.core.settings_service import get_allowed_app_targets

APPLIST_PATH = Path(__file__).resolve().parent / "applist.txt"
WEB_TARGET_ID = "__web__"

_WEB_FALLBACK_URLS = {
    "mozilla firefox": "https://www.mozilla.org/firefox/new/",
    "firefox": "https://www.mozilla.org/firefox/new/",
    "spotify": "https://open.spotify.com/",
    "discord": "https://discord.com/app",
    "google chrome": "https://www.google.com/chrome/",
    "chrome": "https://www.google.com/chrome/",
    "cursor": "https://cursor.com/",
    "vs code": "https://vscode.dev/",
    "visual studio code": "https://vscode.dev/",
    "outlook calendar": "https://outlook.live.com/calendar/",
    "calendar": "https://outlook.live.com/calendar/",
}


@dataclass(frozen=True)
class AppEntry:
    name: str
    command: str
    os_commands: dict[str, str]
    aliases: tuple[str, ...]

    def all_names(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _parse_kv_pairs(raw: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for item in raw.split(";"):
        if not item.strip() or "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            pairs[key] = value
    return pairs


def _parse_app_line(line: str) -> AppEntry | None:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.lower().startswith("format:"):
        return None

    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 2:
        return None

    name = parts[0]
    command = parts[1]
    aliases: List[str] = []
    os_commands: dict[str, str] = {}

    if len(parts) >= 3 and parts[2]:
        aliases = [a.strip() for a in parts[2].split(",") if a.strip()]

    if len(parts) >= 4 and parts[3]:
        os_commands = _parse_kv_pairs(parts[3])

    if not name or not command:
        return None

    return AppEntry(
        name=name,
        command=command,
        os_commands=os_commands,
        aliases=tuple(aliases),
    )


def load_app_list(path: Path = APPLIST_PATH) -> List[AppEntry]:
    if not path.exists():
        return []

    entries: List[AppEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = _parse_app_line(line)
        if entry:
            entries.append(entry)
    return entries


def get_classifier_app_hints(path: Path = APPLIST_PATH) -> str:
    """Build compact app-name/alias hints for the intent classifier prompt."""
    apps = load_app_list(path)
    if not apps:
        return "No apps configured in backend/applist.txt."

    lines = []
    for app in apps:
        aliases = ", ".join(app.aliases) if app.aliases else "(none)"
        lines.append(f"- {app.name} | aliases: {aliases}")
    return "\n".join(lines)


def get_app_control_options(path: Path = APPLIST_PATH) -> list[dict]:
    options = [
        {
            "target_id": WEB_TARGET_ID,
            "label": "Web links in browser",
            "kind": "web",
        }
    ]
    for app in load_app_list(path):
        options.append(
            {
                "target_id": app.name,
                "label": app.name,
                "kind": "app",
            }
        )
    return options


def get_default_allowed_app_targets(path: Path = APPLIST_PATH) -> list[str]:
    return [item["target_id"] for item in get_app_control_options(path)]


def get_app_control_snapshot(path: Path = APPLIST_PATH) -> dict:
    options = get_app_control_options(path)
    default_allowed = [item["target_id"] for item in options]
    allowed = get_allowed_app_targets(default=default_allowed)
    allowed_lower = {item.strip().lower() for item in allowed}

    return {
        "options": [
            {
                **item,
                "allowed": item["target_id"].strip().lower() in allowed_lower,
            }
            for item in options
        ],
        "allowed_targets": allowed,
    }


def add_allowed_app_target(target_id: str, path: Path = APPLIST_PATH) -> list[str]:
    value = str(target_id or "").strip()
    if not value:
        return get_app_control_snapshot(path).get("allowed_targets", [])

    snapshot = get_app_control_snapshot(path)
    existing = list(snapshot.get("allowed_targets", []) or [])
    lowered_existing = {str(item).strip().lower() for item in existing}
    if value.strip().lower() not in lowered_existing:
        existing.append(value)

    from backend.core.settings_service import save_allowed_app_targets

    save_allowed_app_targets(existing)
    return existing


def _is_target_allowed(target_id: str, path: Path = APPLIST_PATH) -> bool:
    snapshot = get_app_control_snapshot(path)
    allowed = {str(item).strip().lower() for item in snapshot.get("allowed_targets", [])}
    return str(target_id or "").strip().lower() in allowed


def resolve_open_app_request(app_name: str, path: Path = APPLIST_PATH) -> dict:
    raw = (app_name or "").strip()
    if _is_direct_url_target(raw):
        return {
            "status": "direct_url",
            "requested_name": raw,
            "display_name": _normalize_direct_url_target(raw),
            "target_id": WEB_TARGET_ID,
            "allowed": _is_target_allowed(WEB_TARGET_ID, path),
            "can_suggest_allow": True,
        }

    apps = load_app_list(path)
    if not apps:
        return {
            "status": "no_apps_configured",
            "requested_name": raw,
            "display_name": raw,
            "target_id": "",
            "allowed": False,
            "can_suggest_allow": False,
        }

    matches = _find_matches(raw, apps)
    if not matches:
        return {
            "status": "not_found",
            "requested_name": raw,
            "display_name": raw,
            "target_id": "",
            "allowed": False,
            "can_suggest_allow": False,
            "available": sorted({a.name for a in apps}),
            "suggestions": _suggest_app_names(raw, apps),
        }

    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "requested_name": raw,
            "display_name": raw,
            "target_id": "",
            "allowed": False,
            "can_suggest_allow": False,
            "matches": sorted({a.name for a in matches}),
        }

    app = matches[0]
    command = _resolve_command(app)
    desktop_available = _ensure_command_exists(command)
    return {
        "status": "app",
        "requested_name": raw,
        "display_name": app.name,
        "target_id": app.name,
        "allowed": _is_target_allowed(app.name, path),
        "can_suggest_allow": True,
        "desktop_available": desktop_available,
        "fallback_url": _fallback_url(app, raw),
    }


def _find_matches(app_name: str, apps: Iterable[AppEntry]) -> List[AppEntry]:
    needle = _normalize(app_name)
    if not needle:
        return []

    exact: List[AppEntry] = []
    loose: List[AppEntry] = []

    for app in apps:
        names = [_normalize(n) for n in app.all_names()]
        if needle in names:
            exact.append(app)
            continue
        if any(needle in n or n in needle for n in names):
            loose.append(app)

    return exact or loose


def _dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        results.append(cleaned)
    return results


def _format_name_list(values: Iterable[str], limit: int = 4) -> str:
    items = _dedupe_preserving_order(values)
    if not items:
        return ""

    trimmed = items[:limit]
    if len(items) > limit:
        trimmed.append(f"{len(items) - limit} more")
    return ", ".join(trimmed)


def _suggest_app_names(requested_name: str, apps: Iterable[AppEntry], limit: int = 3) -> list[str]:
    entries = list(apps)
    if not entries:
        return []

    alias_to_name: dict[str, str] = {}
    for app in entries:
        for alias in app.all_names():
            alias_to_name[_normalize(alias)] = app.name

    candidates = difflib.get_close_matches(
        _normalize(requested_name),
        list(alias_to_name.keys()),
        n=limit * 2,
        cutoff=0.45,
    )
    suggestions: list[str] = []
    for candidate in candidates:
        app_name = alias_to_name.get(candidate)
        if app_name and app_name not in suggestions:
            suggestions.append(app_name)
        if len(suggestions) >= limit:
            break
    return suggestions


def build_open_app_guidance(app_name: str, path: Path = APPLIST_PATH) -> str:
    resolution = resolve_open_app_request(app_name, path)
    status = str(resolution.get("status") or "")
    requested_name = str(resolution.get("requested_name") or app_name).strip() or str(app_name or "").strip()
    display_name = str(resolution.get("display_name") or requested_name).strip() or requested_name

    if status == "direct_url":
        if resolution.get("allowed"):
            return f"Open {display_name} in your browser."
        return (
            "Opening web links is blocked by your security settings. "
            "Allow 'Web links in browser' in Settings > Security."
        )

    if status == "no_apps_configured":
        return "No apps are configured yet. Add entries to backend/features/open_app/applist.txt."

    if status == "not_found":
        suggestions = resolution.get("suggestions") or []
        if suggestions:
            return (
                f"I couldn't find '{requested_name}'. "
                f"Try one of these instead: {_format_name_list(suggestions)}."
            )
        available = resolution.get("available") or []
        if available:
            return (
                f"I couldn't find '{requested_name}'. "
                f"Available apps: {_format_name_list(available)}."
            )
        return f"I couldn't find '{requested_name}'."

    if status == "ambiguous":
        matches = resolution.get("matches") or []
        return (
            f"I found multiple matches for '{requested_name}': {_format_name_list(matches)}. "
            "Say the exact app name you want."
        )

    if status == "app" and not resolution.get("allowed"):
        return (
            f"Opening {display_name} is blocked by your security settings. "
            "Allow it in Settings > Security."
        )

    if status == "app" and not resolution.get("desktop_available", True):
        fallback_url = str(resolution.get("fallback_url") or "").strip()
        if fallback_url:
            return f"{display_name} is not installed here, so I can open its web fallback instead."
        return f"{display_name} is not installed here, so I can try a browser fallback instead."

    return f"Open {display_name}."


def get_open_app_confirmation_summary(app_name: str, path: Path = APPLIST_PATH) -> str:
    resolution = resolve_open_app_request(app_name, path)
    status = str(resolution.get("status") or "")
    display_name = str(resolution.get("display_name") or app_name).strip() or str(app_name or "").strip()

    if status == "direct_url":
        return f"open '{display_name}' in your browser"
    if status == "app" and not resolution.get("desktop_available", True):
        return f"open '{display_name}' in your browser because the desktop app is unavailable"
    if status == "app":
        return f"open '{display_name}'"
    app = str(app_name or "").strip()
    return f"open '{app}'" if app else "open that app"


def _expand(command: str) -> str:
    """Expand %ENV_VAR% and ~/… in a command string."""
    return os.path.expandvars(os.path.expanduser(command))


def _extract_exe_win(expanded: str) -> str:
    """
    Pull just the executable token from a Windows command string.
    Handles both quoted paths ("C:\\foo\\bar.exe" /args) and unquoted ones.
    """
    expanded = expanded.strip()
    if expanded.startswith('"'):
        end = expanded.find('"', 1)
        return expanded[1:end] if end != -1 else expanded[1:]
    return expanded.split()[0] if expanded.split() else ""


def _ensure_command_exists(command: str) -> bool:
    """
    Return True only if the executable referenced by `command` can actually
    be found on disk or on PATH.

    Key fix: expand %ENV_VARS% BEFORE inspecting the path, and on Windows
    avoid shlex (it mangles backslashes).
    """
    expanded = _expand(command).strip()
    if not expanded:
        return False

    if sys.platform.startswith("win"):
        exe = _extract_exe_win(expanded)
        if not exe:
            return False
        exe_path = Path(exe)
        if exe_path.is_absolute():
            return exe_path.exists()
        return shutil.which(exe) is not None
    else:
        try:
            parts = shlex.split(expanded)
        except ValueError:
            return False
        if not parts:
            return False
        exe = parts[0]
        if Path(exe).is_absolute():
            return Path(exe).exists()
        return shutil.which(exe) is not None


def _launch_command(command: str) -> None:
    """
    Launch `command`, expanding env vars first.
    On Windows pass the raw command string directly to CreateProcess to avoid
    shell injection while still allowing quoted executable paths and arguments.
    """
    expanded = _expand(command).strip()
    if not expanded:
        raise RuntimeError("Empty launch command.")

    if sys.platform.startswith("win"):
        subprocess.Popen(expanded)
    else:
        parts = shlex.split(expanded)
        if not parts:
            raise RuntimeError("Empty launch command.")
        subprocess.Popen(parts)


def _platform_key() -> str:
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def _resolve_command(app: AppEntry) -> str:
    key = _platform_key()
    return app.os_commands.get(key, app.command)


def _fallback_url(app: AppEntry, requested_name: str) -> str:
    for name in app.all_names():
        key = _normalize(name)
        if key in _WEB_FALLBACK_URLS:
            return _WEB_FALLBACK_URLS[key]

    normalized_app_name = _normalize(app.name)
    if normalized_app_name in _WEB_FALLBACK_URLS:
        return _WEB_FALLBACK_URLS[normalized_app_name]

    query = quote_plus((requested_name or app.name or "").strip())
    return f"https://www.google.com/search?q={query}"


def _open_fallback_in_browser(app: AppEntry, requested_name: str) -> str:
    url = _fallback_url(app, requested_name)
    opened = webbrowser.open(url, new=2)
    if opened:
        return f"Desktop app unavailable. Opened web fallback for {app.name}: {url}"
    return f"Desktop app unavailable and browser fallback could not be opened for {app.name}."


def _is_direct_url_target(value: str) -> bool:
    raw = (value or "").strip()
    if not raw or " " in raw:
        return False

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return True

    if raw.lower().startswith("localhost:"):
        return True

    return bool(
        re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d+)?(?:/.*)?", raw, re.IGNORECASE)
    )


def _normalize_direct_url_target(value: str) -> str:
    raw = (value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return raw
    return f"https://{raw}" if not raw.lower().startswith("localhost:") else f"http://{raw}"


def _open_direct_url_target(value: str) -> str:
    url = _normalize_direct_url_target(value)
    opened = webbrowser.open(url, new=2)
    if opened:
        return f"Opened {url}."
    return f"Could not open {url} in the browser."


def open_app(app_name: str) -> str:
    resolution = resolve_open_app_request(app_name)

    if resolution["status"] == "direct_url":
        if not resolution["allowed"]:
            return build_open_app_guidance(app_name)
        return _open_direct_url_target(app_name)

    if resolution["status"] == "no_apps_configured":
        return build_open_app_guidance(app_name)

    if resolution["status"] == "not_found":
        return build_open_app_guidance(app_name)

    if resolution["status"] == "ambiguous":
        return build_open_app_guidance(app_name)

    apps = load_app_list()
    matches = _find_matches(app_name, apps)
    app = matches[0]
    if not resolution["allowed"]:
        return build_open_app_guidance(app_name)
    command = _resolve_command(app)
    if not _ensure_command_exists(command):
        return _open_fallback_in_browser(app, app_name)

    try:
        _launch_command(command)
    except Exception as exc:
        fallback_result = _open_fallback_in_browser(app, app_name)
        return f"Failed to open {app.name}: {exc}. {fallback_result}"

    return f"Opened {app.name}."
