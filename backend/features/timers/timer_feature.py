"""In-house timer and alarm feature for Quacky."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import threading


_MAX_TIMER_SECONDS = 7 * 24 * 60 * 60


@dataclass
class _TimerEntry:
    timer_id: str
    kind: str  # "timer" | "alarm"
    trigger_at: datetime
    label: str
    created_at: datetime
    fired: bool = False
    canceled: bool = False


class _TimerManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._counter = 0
        self._entries: dict[str, _TimerEntry] = {}

    def _next_id(self) -> str:
        self._counter += 1
        return f"TMR-{self._counter:04d}"

    def create_timer(self, seconds: int, label: str = "") -> _TimerEntry:
        now = datetime.now()
        trigger = now + timedelta(seconds=max(1, seconds))
        with self._lock:
            entry = _TimerEntry(
                timer_id=self._next_id(),
                kind="timer",
                trigger_at=trigger,
                label=label.strip(),
                created_at=now,
            )
            self._entries[entry.timer_id] = entry
            return entry

    def create_alarm(self, trigger_at: datetime, label: str = "") -> _TimerEntry:
        now = datetime.now()
        with self._lock:
            entry = _TimerEntry(
                timer_id=self._next_id(),
                kind="alarm",
                trigger_at=trigger_at,
                label=label.strip(),
                created_at=now,
            )
            self._entries[entry.timer_id] = entry
            return entry

    def cancel(self, timer_ref: str) -> _TimerEntry | None:
        ref = (timer_ref or "").strip().lower()
        if not ref:
            return None
        with self._lock:
            for entry in self._entries.values():
                if entry.canceled or entry.fired:
                    continue
                if entry.timer_id.lower() == ref:
                    entry.canceled = True
                    return entry
            for entry in self._entries.values():
                if entry.canceled or entry.fired:
                    continue
                if ref in entry.timer_id.lower():
                    entry.canceled = True
                    return entry
            for entry in self._entries.values():
                if entry.canceled or entry.fired:
                    continue
                if entry.label and ref in entry.label.lower():
                    entry.canceled = True
                    return entry
        return None

    def list_active(self) -> list[_TimerEntry]:
        now = datetime.now()
        with self._lock:
            active = [
                e for e in self._entries.values() if not e.canceled and not e.fired
            ]
        return sorted(active, key=lambda e: (e.trigger_at - now).total_seconds())

    def drain_due_alerts(self) -> list[str]:
        now = datetime.now()
        due: list[str] = []
        with self._lock:
            for entry in self._entries.values():
                if entry.canceled or entry.fired:
                    continue
                if entry.trigger_at <= now:
                    entry.fired = True
                    label = f" ({entry.label})" if entry.label else ""
                    kind = "Timer" if entry.kind == "timer" else "Alarm"
                    due.append(f"{kind} {entry.timer_id}{label} is due now.")
        return due


_MANAGER = _TimerManager()


def _parse_alarm_time(alarm_time: str) -> datetime | None:
    raw = (alarm_time or "").strip().lower()
    if not raw:
        return None

    now = datetime.now()
    base = now
    text = raw
    if text.startswith("tomorrow "):
        base = now + timedelta(days=1)
        text = text[len("tomorrow ") :].strip()
    elif text.startswith("today "):
        text = text[len("today ") :].strip()
    if text.startswith("at "):
        text = text[len("at ") :].strip()

    formats = (
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%I:%M %p",
        "%I %p",
        "%H:%M",
        "%H",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue

        if "%Y-%m-%d" in fmt:
            dt = parsed
        else:
            dt = base.replace(
                hour=parsed.hour,
                minute=parsed.minute,
                second=0,
                microsecond=0,
            )
            if dt <= now:
                dt += timedelta(days=1)
        return dt

    return None


def _format_remaining(delta: timedelta) -> str:
    total = max(0, int(delta.total_seconds()))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def set_timer(duration_seconds: int, label: str = "") -> str:
    """Set an in-house timer using a duration in seconds."""
    seconds = int(duration_seconds or 0)
    if seconds <= 0:
        return "Timer duration must be greater than zero seconds."
    if seconds > _MAX_TIMER_SECONDS:
        return "Timer is too long. Maximum supported duration is 7 days."

    entry = _MANAGER.create_timer(seconds=seconds, label=label)
    label_suffix = f" ({entry.label})" if entry.label else ""
    due_text = entry.trigger_at.strftime("%Y-%m-%d %I:%M:%S %p")
    return f"Set timer {entry.timer_id}{label_suffix}. It will ring at {due_text}."


def set_alarm(alarm_time: str, label: str = "") -> str:
    """Set an in-house alarm at a specific time."""
    trigger_at = _parse_alarm_time(alarm_time)
    if trigger_at is None:
        return (
            "Could not parse alarm time. Try formats like "
            "'7:30 AM', '19:30', 'tomorrow 8:00', or '2026-03-20 09:15'."
        )

    entry = _MANAGER.create_alarm(trigger_at=trigger_at, label=label)
    label_suffix = f" ({entry.label})" if entry.label else ""
    due_text = entry.trigger_at.strftime("%Y-%m-%d %I:%M:%S %p")
    return f"Set alarm {entry.timer_id}{label_suffix} for {due_text}."


def list_timers() -> str:
    """List active timers and alarms."""
    active = _MANAGER.list_active()
    if not active:
        return "No active timers or alarms."

    now = datetime.now()
    lines = ["Active timers and alarms:"]
    for entry in active:
        remaining = _format_remaining(entry.trigger_at - now)
        label = f" ({entry.label})" if entry.label else ""
        kind = "Timer" if entry.kind == "timer" else "Alarm"
        due = entry.trigger_at.strftime("%Y-%m-%d %I:%M:%S %p")
        lines.append(f"- {kind} {entry.timer_id}{label}: due {due} ({remaining} remaining)")
    return "\n".join(lines)


def get_active_timers_data() -> list[dict]:
    """Return active timers/alarms in a structured form for UI dashboards."""
    now = datetime.now()
    items: list[dict] = []
    for entry in _MANAGER.list_active():
        remaining_seconds = max(0, int((entry.trigger_at - now).total_seconds()))
        items.append(
            {
                "timer_id": entry.timer_id,
                "kind": entry.kind,
                "label": entry.label,
                "due_at": entry.trigger_at.isoformat(timespec="seconds"),
                "created_at": entry.created_at.isoformat(timespec="seconds"),
                "remaining_seconds": remaining_seconds,
                "remaining_text": _format_remaining(entry.trigger_at - now),
            }
        )
    return items


def cancel_timer(timer_ref: str) -> str:
    """Cancel an existing timer or alarm by id or label text."""
    ref = (timer_ref or "").strip()
    if not ref:
        return "Please provide a timer id or label to cancel."

    entry = _MANAGER.cancel(ref)
    if entry is None:
        return f"Could not find an active timer/alarm matching '{ref}'."

    kind = "Timer" if entry.kind == "timer" else "Alarm"
    label = f" ({entry.label})" if entry.label else ""
    return f"Canceled {kind} {entry.timer_id}{label}."


def drain_due_alerts() -> list[str]:
    """Return and clear newly due timer/alarm alerts."""
    return _MANAGER.drain_due_alerts()
