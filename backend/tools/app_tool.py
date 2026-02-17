"""
App tool wrapper for Quacky.
"""

from backend.features.open_app import open_app as open_app_feature

def open_app(app_name: str) -> str:
    """
    Open an application by name using the open_app feature.
    """
    app_name = (app_name or "").strip()
    if not app_name:
        return "Missing app name."
    return open_app_feature(app_name)
