"""
Persistent JSON-backed session memory store.
"""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SESSION_MEMORY_PATH = Path(__file__).resolve().parent.parent / "data" / "session_memory.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SessionMemoryStore:
    def __init__(self, path: str | Path | None = None):
        env_path = os.getenv("QUACKY_SESSION_MEMORY_PATH", "").strip()
        chosen = path or env_path or DEFAULT_SESSION_MEMORY_PATH
        self.path = Path(chosen)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_doc(self._empty_doc())

    def _empty_doc(self) -> dict:
        return {"version": 1, "updated_at": _utc_now_iso(), "sessions": {}}

    def _empty_session(self) -> dict:
        return {
            "last_topic": "",
            "pending_action": None,
            "preferences": {},
            "facts": {},
            "active_tasks": [],
            "updated_at": _utc_now_iso(),
        }

    def _read_doc(self) -> dict:
        if not self.path.exists():
            return self._empty_doc()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return self._empty_doc()
        if not isinstance(raw, dict):
            return self._empty_doc()
        sessions = raw.get("sessions")
        if not isinstance(sessions, dict):
            raw["sessions"] = {}
        raw.setdefault("version", 1)
        raw.setdefault("updated_at", _utc_now_iso())
        return raw

    def _write_doc(self, doc: dict) -> None:
        doc["updated_at"] = _utc_now_iso()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)

    def _normalize_session(self, session: dict | None) -> dict:
        base = self._empty_session()
        if isinstance(session, dict):
            last_topic = session.get("last_topic")
            if isinstance(last_topic, str):
                base["last_topic"] = last_topic.strip()

            pending_action = session.get("pending_action")
            if isinstance(pending_action, dict):
                base["pending_action"] = pending_action

            preferences = session.get("preferences")
            if isinstance(preferences, dict):
                base["preferences"] = {
                    str(k).strip(): str(v).strip()
                    for k, v in preferences.items()
                    if str(k).strip() and str(v).strip()
                }

            facts = session.get("facts")
            if isinstance(facts, dict):
                base["facts"] = {
                    str(k).strip(): str(v).strip()
                    for k, v in facts.items()
                    if str(k).strip() and str(v).strip()
                }

            tasks = session.get("active_tasks")
            if isinstance(tasks, list):
                cleaned = [str(t).strip() for t in tasks if str(t).strip()]
                # Keep order, remove duplicates
                deduped = list(dict.fromkeys(cleaned))
                base["active_tasks"] = deduped[:100]

        base["updated_at"] = _utc_now_iso()
        return base

    def get_session(self, chat_id: str) -> dict:
        key = (chat_id or "").strip() or "default"
        with self._lock:
            doc = self._read_doc()
            session = doc["sessions"].get(key)
            return self._normalize_session(session)

    def save_session(self, chat_id: str, session: dict) -> None:
        key = (chat_id or "").strip() or "default"
        with self._lock:
            doc = self._read_doc()
            doc["sessions"][key] = self._normalize_session(session)
            self._write_doc(doc)

    def delete_session(self, chat_id: str) -> None:
        key = (chat_id or "").strip() or "default"
        with self._lock:
            doc = self._read_doc()
            doc.get("sessions", {}).pop(key, None)
            self._write_doc(doc)

    def remember_fact(self, chat_id: str, key: str, value: str) -> None:
        fact_key = (key or "").strip()
        fact_value = (value or "").strip()
        if not fact_key or not fact_value:
            raise ValueError("key and value are required.")
        session = self.get_session(chat_id)
        session["facts"][fact_key] = fact_value
        self.save_session(chat_id, session)

    def recall_facts(self, chat_id: str, key: str = "") -> dict[str, str]:
        session = self.get_session(chat_id)
        facts = session.get("facts", {})
        if not key:
            return deepcopy(facts)
        value = facts.get(key.strip())
        return {key.strip(): value} if value else {}

    def forget_fact(self, chat_id: str, key: str) -> bool:
        fact_key = (key or "").strip()
        if not fact_key:
            raise ValueError("key is required.")
        session = self.get_session(chat_id)
        removed = fact_key in session.get("facts", {})
        session.get("facts", {}).pop(fact_key, None)
        self.save_session(chat_id, session)
        return removed

    def add_task(self, chat_id: str, task: str) -> None:
        task_text = (task or "").strip()
        if not task_text:
            raise ValueError("task is required.")
        session = self.get_session(chat_id)
        tasks = session.setdefault("active_tasks", [])
        if task_text not in tasks:
            tasks.append(task_text)
        session["active_tasks"] = tasks[:100]
        self.save_session(chat_id, session)

    def complete_task(self, chat_id: str, task: str) -> bool:
        task_text = (task or "").strip()
        if not task_text:
            raise ValueError("task is required.")
        session = self.get_session(chat_id)
        tasks = session.get("active_tasks", [])
        if task_text not in tasks:
            return False
        session["active_tasks"] = [t for t in tasks if t != task_text]
        self.save_session(chat_id, session)
        return True

    def list_tasks(self, chat_id: str) -> list[str]:
        session = self.get_session(chat_id)
        tasks = session.get("active_tasks", [])
        return list(tasks) if isinstance(tasks, list) else []
