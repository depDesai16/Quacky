"""
App tool wrapper for Quacky.
"""

from backend.features.calendar.calendar_feature import open_outlook_calendar


def open_app(app_name: str) -> str:
    """
    Open an application by name.

    app_name: name of the app to open, e.g. "outlook", "outlook calendar",
              "spotify", "chrome", "vs code"
    """
    normalized = (app_name or "").strip().lower()
    if not normalized:
        return "Missing app name."

    if "calendar" in normalized or "outlook" in normalized:
        try:
            return open_outlook_calendar()
        except Exception as exc:
            return f"Failed to open Outlook calendar: {exc}"

    return f"Opening {app_name}..."