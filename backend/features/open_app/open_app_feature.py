from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import webbrowser
import re
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
}

_URL_WITH_SCHEME_RE = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)
_URL_WWW_RE = re.compile(r"(www\.[^\s]+)", re.IGNORECASE)
_URL_LOCALHOST_RE = re.compile(
    r"\b(localhost|127\.0\.0\.1)(?::\d{2,5})?(?:/[^\s]*)?\b",
    re.IGNORECASE,
)
_URL_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?::\d{2,5})?(?:/[^\s]*)?\b",
    re.IGNORECASE,
)
_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)
_LIKELY_FILE_EXTENSIONS = {
    "py", "txt", "md", "json", "yaml", "yml", "xml", "csv",
    "js", "ts", "jsx", "tsx", "java", "c", "cc", "cpp", "h", "hpp",
    "go", "rs", "rb", "php", "swift", "kt", "sql", "log", "ini", "toml",
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
    """
    Build compact app-name/alias hints for the intent classifier prompt.
    """
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


def _ensure_command_exists(command: str) -> bool:
    if command.startswith("terminal:"):
        return True
    parts = shlex.split(command)
    if not parts:
        return False
    exe = parts[0]
    if Path(exe).is_absolute():
        return Path(exe).exists()
    return shutil.which(exe) is not None


def _launch_command(command: str) -> None:
    if command.startswith("terminal:"):
        _launch_in_new_terminal(command.split(":", 1)[1].strip())
        return
    parts = shlex.split(command)
    if not parts:
        raise RuntimeError("Empty launch command.")
    _popen_detached(parts)


def _popen_detached(cmd, *, shell: bool = False) -> None:
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "shell": shell,
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def _launch_in_new_terminal(inner_command: str) -> None:
    if not inner_command:
        raise RuntimeError("Empty terminal command.")

    if sys.platform.startswith("win"):
        # Open a new cmd window and run the command.
        _popen_detached(f'start "" cmd /k "{inner_command}"', shell=True)
        return

    if sys.platform.startswith("darwin"):
        # Tell Terminal.app to open a new tab/window and run the command.
        script = f'tell application "Terminal" to do script "{inner_command}"'
        _popen_detached(["osascript", "-e", script])
        return

    # Linux and other Unix: use first available terminal emulator.
    candidates = [
        ["x-terminal-emulator", "-e", inner_command],
        ["gnome-terminal", "--", "bash", "-lc", inner_command],
        ["konsole", "-e", "bash", "-lc", inner_command],
        ["xfce4-terminal", "-x", "bash", "-lc", inner_command],
        ["xterm", "-e", inner_command],
        ["kitty", "bash", "-lc", inner_command],
        ["alacritty", "-e", "bash", "-lc", inner_command],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            _popen_detached(cmd)
            return

    raise RuntimeError("No terminal emulator found for terminal: command.")


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
        return f"Desktop app unavailable. Opened web fallback for {app.name}"
    return f"Desktop app unavailable and browser fallback could not be opened for {app.name}."


def _clean_url_candidate(candidate: str) -> str:
    # Strip trailing punctuation commonly attached to spoken/written commands.
    return candidate.strip().rstrip(".,;:!?)]}\"'")


def _is_probably_filename(candidate: str) -> bool:
    token = candidate.lower().split("/")[-1]
    if "." not in token:
        return False
    ext = token.rsplit(".", 1)[-1]
    return ext in _LIKELY_FILE_EXTENSIONS


def _extract_url_candidate(text: str) -> str | None:
    if not text:
        return None

    normalized = re.sub(r"\s+dot\s+", ".", text, flags=re.IGNORECASE)

    for pattern in (_URL_WITH_SCHEME_RE, _URL_WWW_RE, _URL_LOCALHOST_RE, _URL_DOMAIN_RE):
        match = pattern.search(normalized)
        if not match:
            continue
        candidate = _clean_url_candidate(match.group(0))
        if _is_probably_filename(candidate):
            continue
        return candidate

    return None


def _to_browsable_url(candidate: str) -> str:
    if _SCHEME_RE.match(candidate):
        return candidate
    lower = candidate.lower()
    if lower.startswith("localhost") or lower.startswith("127.0.0.1"):
        return f"http://{candidate}"
    return f"https://{candidate}"


def _open_website(candidate: str) -> str:
    url = _to_browsable_url(candidate)
    opened = webbrowser.open(url, new=2)
    if opened:
        return f"Opened website: {url}"
    return f"Could not open website: {url}"


def open_app(app_name: str) -> str:
    url_candidate = _extract_url_candidate(app_name)
    if url_candidate:
        return _open_website(url_candidate)

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