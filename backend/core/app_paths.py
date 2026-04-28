from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Quacky"
ROOT_DIR = Path(__file__).resolve().parents[2]


def executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return ROOT_DIR


def bundle_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        return Path(meipass).resolve()
    return executable_dir()


def resource_path(*parts: str) -> Path:
    return bundle_root().joinpath(*parts)


def user_data_dir() -> Path:
    override = os.getenv("QUACKY_DATA_DIR", "").strip()
    if override:
        path = Path(override).expanduser()
    elif sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        path = Path(base).expanduser() / APP_NAME if base else Path.home() / "AppData" / "Local" / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.getenv("XDG_DATA_HOME", "").strip()
        path = Path(base).expanduser() / APP_NAME if base else Path.home() / ".local" / "share" / APP_NAME

    path.mkdir(parents=True, exist_ok=True)
    return path


def user_data_path(*parts: str) -> Path:
    return user_data_dir().joinpath(*parts)
