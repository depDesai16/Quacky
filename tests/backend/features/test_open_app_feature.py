from pathlib import Path

import pytest

from backend.features.open_app import open_app_feature as mod


def _entry(name: str, command: str, aliases=(), os_commands=None):
    return mod.AppEntry(
        name=name,
        command=command,
        aliases=tuple(aliases),
        os_commands=os_commands or {},
    )


def test_parse_kv_pairs_ignores_invalid_items():
    raw = " linux = firefox ; bad ; windows=cmd /c start firefox ; =skip ; macos= open -a Firefox "
    parsed = mod._parse_kv_pairs(raw)

    assert parsed == {
        "linux": "firefox",
        "windows": "cmd /c start firefox",
        "macos": "open -a Firefox",
    }


def test_parse_app_line_with_aliases_and_os_commands():
    line = "Firefox | firefox | mozilla, browser | linux=firefox; windows=cmd /c start firefox"
    app = mod._parse_app_line(line)

    assert app is not None
    assert app.name == "Firefox"
    assert app.command == "firefox"
    assert app.aliases == ("mozilla", "browser")
    assert app.os_commands["linux"] == "firefox"
    assert app.os_commands["windows"] == "cmd /c start firefox"


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "# comment",
        "NameOnly",
        "| firefox",
        "Firefox | ",
    ],
)
def test_parse_app_line_invalid_cases(line):
    assert mod._parse_app_line(line) is None


def test_load_app_list_reads_valid_lines(tmp_path: Path):
    appfile = tmp_path / "applist.txt"
    appfile.write_text(
        """
# comment
Firefox | firefox | mozilla
InvalidLine
Spotify | spotify | music | linux=spotify-electron
""".strip(),
        encoding="utf-8",
    )

    apps = mod.load_app_list(appfile)

    assert [a.name for a in apps] == ["Firefox", "Spotify"]
    assert apps[0].aliases == ("mozilla",)
    assert apps[1].os_commands["linux"] == "spotify-electron"


def test_get_classifier_app_hints_empty(tmp_path: Path):
    hints = mod.get_classifier_app_hints(tmp_path / "missing.txt")
    assert hints == "No apps configured in backend/applist.txt."


def test_get_classifier_app_hints_with_aliases(tmp_path: Path):
    appfile = tmp_path / "applist.txt"
    appfile.write_text(
        "Firefox | firefox | mozilla\nCalculator | calc\n",
        encoding="utf-8",
    )

    hints = mod.get_classifier_app_hints(appfile)

    assert "- Firefox | aliases: mozilla" in hints
    assert "- Calculator | aliases: (none)" in hints


def test_find_matches_prefers_exact_over_loose():
    apps = [
        _entry("Google Chrome", "chrome", aliases=("chrome",)),
        _entry("Chromium", "chromium", aliases=("chromium",)),
    ]

    matches = mod._find_matches("chrome", apps)

    assert [a.name for a in matches] == ["Google Chrome"]


def test_find_matches_returns_loose_if_no_exact():
    apps = [_entry("Visual Studio Code", "code", aliases=("vscode",))]

    matches = mod._find_matches("visual", apps)

    assert [a.name for a in matches] == ["Visual Studio Code"]


def test_ensure_command_exists_terminal_prefix():
    assert mod._ensure_command_exists("terminal:htop") is True


def test_ensure_command_exists_empty_command():
    assert mod._ensure_command_exists("   ") is False


def test_ensure_command_exists_absolute_path(tmp_path: Path):
    exe = tmp_path / "tool"
    exe.write_text("#!/bin/sh\n", encoding="utf-8")

    assert mod._ensure_command_exists(str(exe)) is True


def test_extract_url_candidate_handles_spoken_dot_and_file_filtering():
    assert mod._extract_url_candidate("open example dot com/docs") == "example.com/docs"
    assert mod._extract_url_candidate("open notes.txt") is None


def test_to_browsable_url_adds_scheme_when_missing():
    assert mod._to_browsable_url("example.com") == "https://example.com"
    assert mod._to_browsable_url("localhost:3000") == "http://localhost:3000"
    assert mod._to_browsable_url("https://x.y") == "https://x.y"


def test_open_website_returns_success_message(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod.webbrowser, "open", lambda *_args, **_kwargs: True)

    result = mod._open_website("example.com")

    assert result == "Opened website: https://example.com"


def test_open_app_prioritizes_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "_open_website", lambda candidate: f"URL:{candidate}")

    result = mod.open_app("please open www.example.com now")

    assert result == "URL:www.example.com"


def test_open_app_no_apps_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "load_app_list", lambda: [])

    result = mod.open_app("spotify")

    assert result == "No apps configured yet. Add entries to backend/applist.txt."


def test_open_app_not_found_lists_available(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        mod,
        "load_app_list",
        lambda: [_entry("Spotify", "spotify"), _entry("Discord", "discord")],
    )

    result = mod.open_app("teams")

    assert result == "App 'teams' not found. Available: Discord, Spotify."


def test_open_app_ambiguous_match(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        mod,
        "load_app_list",
        lambda: [_entry("Google Chrome", "chrome"), _entry("Chromium", "chromium")],
    )

    result = mod.open_app("chrom")

    assert result == "Which app did you mean? Matches: Chromium, Google Chrome."


def test_open_app_fallback_when_command_missing(monkeypatch: pytest.MonkeyPatch):
    app = _entry("Spotify", "spotify")
    monkeypatch.setattr(mod, "load_app_list", lambda: [app])
    monkeypatch.setattr(mod, "_ensure_command_exists", lambda _cmd: False)
    monkeypatch.setattr(mod, "_open_fallback_in_browser", lambda _app, _name: "fallback")

    result = mod.open_app("spotify")

    assert result == "fallback"


def test_open_app_successful_launch(monkeypatch: pytest.MonkeyPatch):
    app = _entry("Spotify", "spotify")
    monkeypatch.setattr(mod, "load_app_list", lambda: [app])
    monkeypatch.setattr(mod, "_ensure_command_exists", lambda _cmd: True)
    monkeypatch.setattr(mod, "_launch_command", lambda _cmd: None)

    result = mod.open_app("spotify")

    assert result == "Opened Spotify."


def test_open_app_launch_exception_uses_fallback(monkeypatch: pytest.MonkeyPatch):
    app = _entry("Spotify", "spotify")
    monkeypatch.setattr(mod, "load_app_list", lambda: [app])
    monkeypatch.setattr(mod, "_ensure_command_exists", lambda _cmd: True)

    def _boom(_cmd):
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "_launch_command", _boom)
    monkeypatch.setattr(mod, "_open_fallback_in_browser", lambda _app, _name: "fallback")

    result = mod.open_app("spotify")

    assert result == "Failed to open Spotify: boom. fallback"
