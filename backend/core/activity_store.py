"""Lightweight persistent store for recent assistant-created calendar actions."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path


_LOCK = threading.Lock()
_FILE = Path(__file__).resolve().parents[1] / "data" / "activity_log.json"
_MAX_EVENTS = 120


def _ensure_parent() -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)


def _default_data() -> dict:
    return {"calendar_events": []}


def _read_data() -> dict:
    _ensure_parent()
    if not _FILE.exists():
        return _default_data()
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _default_data()
    if not isinstance(data, dict):
        return _default_data()
    data.setdefault("calendar_events", [])
    return data


def _write_data(data: dict) -> None:
    _ensure_parent()
    _FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _clean(text: str) -> str:
    return " ".join((text or "").strip().split())


def add_calendar_event(
    action: str,
    title: str,
    start_time: str = "",
    end_time: str = "",
    location: str = "",
    details: str = "",
    status: str = "ok",
    result: str = "",
) -> None:
    record = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "action": _clean(action).lower() or "unknown",
        "title": _clean(title),
        "start_time": _clean(start_time),
        "end_time": _clean(end_time),
        "location": _clean(location),
        "details": _clean(details),
        "status": _clean(status).lower() or "ok",
        "result": _clean(result),
    }
    with _LOCK:
        data = _read_data()
        events = list(data.get("calendar_events") or [])
        events.insert(0, record)
        data["calendar_events"] = events[:_MAX_EVENTS]
        _write_data(data)


def list_calendar_events(limit: int = 25) -> list[dict]:
    wanted = max(0, int(limit))
    with _LOCK:
        data = _read_data()
        raw = list(data.get("calendar_events") or [])
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "created_at": str(item.get("created_at", "")).strip(),
                "action": str(item.get("action", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "start_time": str(item.get("start_time", "")).strip(),
                "end_time": str(item.get("end_time", "")).strip(),
                "location": str(item.get("location", "")).strip(),
                "details": str(item.get("details", "")).strip(),
                "status": str(item.get("status", "")).strip(),
                "result": str(item.get("result", "")).strip(),
            }
        )
        if len(out) >= wanted:
            break
    return out
