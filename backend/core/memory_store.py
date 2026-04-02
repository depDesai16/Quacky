"""Persistent user memory store (preferences and task notes)."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

_LOCK = threading.Lock()
_FILE = Path(__file__).resolve().parents[1] / "data" / "user_memory.json"
_MAX_PREFS = 40
_MAX_TASKS = 80


def _ensure_parent() -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)


def _default_data() -> dict:
    return {"preferences": [], "task_notes": []}


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
    data.setdefault("preferences", [])
    data.setdefault("task_notes", [])
    return data


def _write_data(data: dict) -> None:
    _ensure_parent()
    _FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().split())


def _upsert_item(items: list[dict], value: str, max_items: int) -> list[dict]:
    cleaned = _normalize(value)
    if not cleaned:
        return items

    lowered = cleaned.lower()
    now = datetime.now().isoformat(timespec="seconds")

    found = False
    new_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        existing = _normalize(str(item.get("value", "")))
        if not existing:
            continue
        if existing.lower() == lowered:
            new_items.append({"value": cleaned, "updated_at": now})
            found = True
        else:
            new_items.append(
                {
                    "value": existing,
                    "updated_at": str(item.get("updated_at", now)),
                }
            )

    if not found:
        new_items.append({"value": cleaned, "updated_at": now})

    new_items.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    return new_items[:max_items]


def _remove_item(items: list[dict], value: str) -> tuple[list[dict], bool]:
    needle = _normalize(value).lower()
    if not needle:
        return items, False

    found_exact = False
    filtered: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        existing = _normalize(str(item.get("value", "")))
        if not existing:
            continue
        if existing.lower() == needle and not found_exact:
            found_exact = True
            continue
        filtered.append(
            {
                "value": existing,
                "updated_at": str(item.get("updated_at", "")),
            }
        )

    if found_exact:
        return filtered, True

    found_substring = False
    filtered_sub: list[dict] = []
    for item in filtered:
        existing = _normalize(str(item.get("value", "")))
        if not existing:
            continue
        if needle in existing.lower() and not found_substring:
            found_substring = True
            continue
        filtered_sub.append(item)

    return (filtered_sub, True) if found_substring else (items, False)


def add_preference(value: str) -> None:
    with _LOCK:
        data = _read_data()
        data["preferences"] = _upsert_item(
            list(data.get("preferences") or []), value, _MAX_PREFS
        )
        _write_data(data)


def add_task_note(value: str) -> None:
    with _LOCK:
        data = _read_data()
        data["task_notes"] = _upsert_item(
            list(data.get("task_notes") or []), value, _MAX_TASKS
        )
        _write_data(data)


def forget_preference(value: str) -> bool:
    with _LOCK:
        data = _read_data()
        original = list(data.get("preferences") or [])
        updated, removed = _remove_item(original, value)
        if removed:
            data["preferences"] = updated[:_MAX_PREFS]
            _write_data(data)
        return removed


def forget_task_note(value: str) -> bool:
    with _LOCK:
        data = _read_data()
        original = list(data.get("task_notes") or [])
        updated, removed = _remove_item(original, value)
        if removed:
            data["task_notes"] = updated[:_MAX_TASKS]
            _write_data(data)
        return removed


def clear_preferences() -> int:
    with _LOCK:
        data = _read_data()
        count = len(list(data.get("preferences") or []))
        if count:
            data["preferences"] = []
            _write_data(data)
        return count


def clear_task_notes() -> int:
    with _LOCK:
        data = _read_data()
        count = len(list(data.get("task_notes") or []))
        if count:
            data["task_notes"] = []
            _write_data(data)
        return count


def clear_all_memory() -> tuple[int, int]:
    with _LOCK:
        data = _read_data()
        pref_count = len(list(data.get("preferences") or []))
        task_count = len(list(data.get("task_notes") or []))
        if pref_count or task_count:
            data["preferences"] = []
            data["task_notes"] = []
            _write_data(data)
        return pref_count, task_count


def get_preferences(limit: int = 5) -> list[str]:
    limit = max(0, int(limit))
    with _LOCK:
        data = _read_data()
        items = list(data.get("preferences") or [])
    values = [_normalize(str(item.get("value", ""))) for item in items if isinstance(item, dict)]
    values = [value for value in values if value]
    return values[:limit]


def get_task_notes(limit: int = 8) -> list[str]:
    limit = max(0, int(limit))
    with _LOCK:
        data = _read_data()
        items = list(data.get("task_notes") or [])
    values = [_normalize(str(item.get("value", ""))) for item in items if isinstance(item, dict)]
    values = [value for value in values if value]
    return values[:limit]
