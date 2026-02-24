from backend.tools import app_tool


def test_open_app_missing_name_returns_error():
    assert app_tool.open_app("   ") == "Missing app name."


def test_open_app_delegates_to_feature(monkeypatch):
    monkeypatch.setattr(app_tool, "open_app_feature", lambda name: f"ok:{name}")

    result = app_tool.open_app("   spotify   ")

    assert result == "ok:spotify"
