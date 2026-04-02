from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
from urllib.parse import quote_plus

APPLIST_PATH = Path(__file__).resolve().parent / "applist.txt"

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


def open_app(app_name: str) -> str:
    apps = load_app_list()
    if not apps:
        return "No apps configured yet. Add entries to backend/applist.txt."

    matches = _find_matches(app_name, apps)
    if not matches:
        available = ", ".join(sorted({a.name for a in apps}))
        return f"App '{app_name}' not found. Available: {available}."

    if len(matches) > 1:
        options = ", ".join(sorted({a.name for a in matches}))
        return f"Which app did you mean? Matches: {options}."

    app = matches[0]
    command = _resolve_command(app)
    if not _ensure_command_exists(command):
        return _open_fallback_in_browser(app, app_name)

    try:
        _launch_command(command)
    except Exception as exc:
        fallback_result = _open_fallback_in_browser(app, app_name)
        return f"Failed to open {app.name}: {exc}. {fallback_result}"

    return f"Opened {app.name}."
