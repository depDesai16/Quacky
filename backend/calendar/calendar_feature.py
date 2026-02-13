from __future__ import annotations

import os
import re
import shutil
import subprocess
import time as clock
import webbrowser
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlencode

_RECENT_EVENT_SIGNATURES: dict[tuple[str, str, str], float] = {}
_DEDUP_WINDOW_SECONDS = 120.0


def _find_outlook_executable() -> str | None:
    """Best-effort lookup for Outlook desktop on Windows."""
    if os.name != "nt":
        return None

    found = shutil.which("outlook.exe")
    if found:
        return found

    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft Office" / "root" / "Office16" / "OUTLOOK.EXE",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft Office" / "root" / "Office16" / "OUTLOOK.EXE",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft Office" / "Office16" / "OUTLOOK.EXE",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft Office" / "Office16" / "OUTLOOK.EXE",
    ]
    for path in candidates:
        if str(path).strip() and path.exists():
            return str(path)
    return None


def open_outlook_calendar() -> str:
    """Open desktop Outlook calendar when available; otherwise open Outlook web calendar."""
    web_url = "https://outlook.office.com/calendar/view/month"
    if os.name == "nt":
        outlook_exe = _find_outlook_executable()
        if outlook_exe:
            try:
                os.startfile("outlookcal:")  
                return "Opened Outlook Calendar desktop app."
            except Exception:
                try:
                    subprocess.Popen([outlook_exe, "/select", "outlook:calendar"])
                    return "Opened Outlook Calendar desktop app."
                except Exception:
                    pass

    webbrowser.open(web_url, new=2)
    return "Opened Outlook web calendar."


def _parse_time_component(value: str) -> tuple[int, int] | None:
    text = (value or "").strip().lower()
    if not text:
        return None

    if "noon" in text:
        return (12, 0)
    if "midnight" in text:
        return (0, 0)

    match = re.search(r"\b(\d{1,2})(?::([0-5]\d))?\s*(am|pm)\b", text)
    if match:
        hour = int(match.group(1)) % 12
        minute = int(match.group(2) or "0")
        if match.group(3) == "pm":
            hour += 12
        return (hour, minute)

    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
    if match:
        return (int(match.group(1)), int(match.group(2)))

    return None


def _parse_relative_datetime(value: str, default_time: tuple[int, int]) -> datetime | None:
    text = (value or "").strip().lower()
    now = datetime.now()

    if "tomorrow" in text:
        base_date = (now + timedelta(days=1)).date()
    elif "today" in text:
        base_date = now.date()
    else:
        return None

    parsed_time = _parse_time_component(text) or default_time
    return datetime.combine(base_date, time(parsed_time[0], parsed_time[1]))


def _parse_common_datetime(value: str, default_time: tuple[int, int]) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %I %p",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %I %p",
        "%m/%d/%Y",
    ]
    for dt_format in formats:
        try:
            parsed = datetime.strptime(raw, dt_format)
            if dt_format.endswith("%Y-%m-%d") or dt_format.endswith("%m/%d/%Y"):
                return datetime.combine(parsed.date(), time(default_time[0], default_time[1]))
            return parsed
        except ValueError:
            continue
    return None


def _parse_time_only_for_date(value: str, base_date: date) -> datetime | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    normalized = re.sub(r"^\s*at\s+", "", text)
    parsed_time = _parse_time_component(normalized)
    if not parsed_time:
        return None
    if re.fullmatch(r"(?:\d{1,2}(?::[0-5]\d)?\s*(?:am|pm)?|[01]?\d|2[0-3]:[0-5]\d|noon|midnight)", normalized):
        return datetime.combine(base_date, time(parsed_time[0], parsed_time[1]))
    return None


def _parse_event_datetime(
    value: str,
    field_name: str,
    default_time: tuple[int, int],
    reference_date: date | None = None,
) -> datetime:
    parsed_raw = (value or "").strip()
    if not parsed_raw:
        raise ValueError(f"{field_name} is required.")

    if reference_date is not None:
        parsed_time_only = _parse_time_only_for_date(parsed_raw, reference_date)
        if parsed_time_only is not None:
            return parsed_time_only

    parsed_relative = _parse_relative_datetime(parsed_raw, default_time)
    if parsed_relative is not None:
        return parsed_relative

    parsed_common = _parse_common_datetime(parsed_raw, default_time)
    if parsed_common is not None:
        return parsed_common

    iso_raw = parsed_raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_raw)
    except ValueError:
        pass

    raise ValueError(
        f"{field_name} must be like '2026-02-13T14:30', 'tomorrow 3pm', or '02/13/2026 15:30'."
    )


def _create_outlook_event_desktop(
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    location: str = "",
    details: str = "",
) -> str:
    if os.name != "nt":
        raise RuntimeError("Desktop Outlook event creation is supported on Windows only.")

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise RuntimeError("pywin32 is required for desktop Outlook event creation.") from exc

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        appointment = outlook.CreateItem(1)
        appointment.Subject = title
        appointment.Start = start_dt.strftime("%m/%d/%Y %H:%M")
        appointment.Duration = int((end_dt - start_dt).total_seconds() // 60)
        appointment.End = end_dt.strftime("%m/%d/%Y %H:%M")
        appointment.Location = location
        appointment.Body = details
        appointment.Save()
    finally:
        pythoncom.CoUninitialize()

    return (
        f"Added Outlook event '{title}' from {start_dt.isoformat()} to {end_dt.isoformat()}."
    )


def _to_local_naive(dt_value: datetime) -> datetime:
    """Convert timezone-aware datetimes to local wall time for Outlook desktop."""
    if dt_value.tzinfo is None:
        return dt_value
    return dt_value.astimezone().replace(tzinfo=None)


def _to_outlook_web_datetime(dt_value: datetime) -> str:
    """Format datetime with explicit offset so Outlook web won't reinterpret local time."""
    if dt_value.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        dt_value = dt_value.replace(tzinfo=local_tz)
    return dt_value.isoformat(timespec="seconds")


def _event_signature(title: str, start_dt: datetime, end_dt: datetime) -> tuple[str, str, str]:
    return (
        title.strip().lower(),
        start_dt.isoformat(timespec="minutes"),
        end_dt.isoformat(timespec="minutes"),
    )


def _is_recent_duplicate(signature: tuple[str, str, str]) -> bool:
    now = clock.monotonic()
    cutoff = now - _DEDUP_WINDOW_SECONDS

    stale = [key for key, ts in _RECENT_EVENT_SIGNATURES.items() if ts < cutoff]
    for key in stale:
        _RECENT_EVENT_SIGNATURES.pop(key, None)

    seen_at = _RECENT_EVENT_SIGNATURES.get(signature)
    if seen_at is None:
        return False
    return seen_at >= cutoff


def _mark_event_signature(signature: tuple[str, str, str]) -> None:
    _RECENT_EVENT_SIGNATURES[signature] = clock.monotonic()


def create_outlook_event(
    title: str,
    start_time: str,
    end_time: str = "",
    duration_minutes: int = 60,
    location: str = "",
    details: str = "",
) -> str:
    """Create and save an Outlook event; falls back to web compose when desktop save fails."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ValueError("title is required.")

    start_dt = _parse_event_datetime(
        start_time,
        "start_time",
        default_time=(9, 0),
    )

    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than 0.")

    clean_end = (end_time or "").strip()
    if clean_end:
        end_dt = _parse_event_datetime(
            clean_end,
            "end_time",
            default_time=(start_dt.hour, start_dt.minute),
            reference_date=start_dt.date(),
        )
    else:
        end_dt = start_dt + timedelta(minutes=duration_minutes)

    if end_dt <= start_dt:
        raise ValueError("end_time must be after start_time.")

    start_dt = _to_local_naive(start_dt)
    end_dt = _to_local_naive(end_dt)

    clean_location = (location or "").strip()
    clean_details = (details or "").strip()
    signature = _event_signature(clean_title, start_dt, end_dt)
    if _is_recent_duplicate(signature):
        return (
            f"Skipped duplicate event '{clean_title}' from "
            f"{start_dt.isoformat()} to {end_dt.isoformat()}."
        )

    try:
        result = _create_outlook_event_desktop(
            title=clean_title,
            start_dt=start_dt,
            end_dt=end_dt,
            location=clean_location,
            details=clean_details,
        )
        _mark_event_signature(signature)
        return result
    except Exception:
        pass

    query = urlencode(
        {
            "path": "/calendar/action/compose",
            "rru": "addevent",
            "subject": clean_title,
            "startdt": _to_outlook_web_datetime(start_dt),
            "enddt": _to_outlook_web_datetime(end_dt),
            "location": clean_location,
            "body": clean_details,
        }
    )
    compose_url = f"https://outlook.office.com/calendar/0/deeplink/compose?{query}"
    webbrowser.open(compose_url, new=2)

    location_msg = f" at {clean_location}" if clean_location else ""
    return (
        f"Could not auto-save in desktop Outlook. Opened web event form for '{clean_title}' from "
        f"{start_dt.isoformat()} to {end_dt.isoformat()}{location_msg}."
    )

def update_outlook_event(
    title: str,
    new_start_time: str,
    new_end_time: str = "",
    new_duration_minutes: int = 0,
) -> str:
    """Find an existing Outlook event by title and update its start/end time."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ValueError("title is required.")

    new_start_dt = _parse_event_datetime(
        new_start_time,
        "new_start_time",
        default_time=(9, 0),
    )

    if new_end_time.strip():
        new_end_dt = _parse_event_datetime(
            new_end_time,
            "new_end_time",
            default_time=(new_start_dt.hour, new_start_dt.minute),
            reference_date=new_start_dt.date(),
        )
    elif new_duration_minutes > 0:
        new_end_dt = new_start_dt + timedelta(minutes=new_duration_minutes)
    else:
        new_end_dt = None

    new_start_dt = _to_local_naive(new_start_dt)
    if new_end_dt:
        new_end_dt = _to_local_naive(new_end_dt)

    if os.name != "nt":
        return "Updating desktop Outlook events is only supported on Windows."

    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return "pywin32 is required to update Outlook events."

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        calendar = namespace.GetDefaultFolder(9)
        items = calendar.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")

        found = items.Find(f"[Subject] = '{clean_title}'")
        if not found:
            return f"Could not find an event named '{clean_title}' in your Outlook calendar."

        old_start = found.Start
        old_end = found.End

        found.Start = new_start_dt.strftime("%m/%d/%Y %H:%M")
        if new_end_dt:
            found.End = new_end_dt.strftime("%m/%d/%Y %H:%M")
            found.Duration = int((new_end_dt - new_start_dt).total_seconds() // 60)
        else:
            try:
                old_duration = int((old_end - old_start).total_seconds() // 60)
            except Exception:
                old_duration = 60
            shifted_end = new_start_dt + timedelta(minutes=old_duration)
            found.End = shifted_end.strftime("%m/%d/%Y %H:%M")
            found.Duration = old_duration

        found.Save()

        end_display = new_end_dt or (new_start_dt + timedelta(minutes=found.Duration))
        return (
            f"Updated '{clean_title}' to {new_start_dt.isoformat()} "
            f"– {end_display.isoformat()}."
        )

    finally:
        pythoncom.CoUninitialize()

def delete_outlook_event(title: str) -> str:
    """Find an existing Outlook event by title and delete it."""
    clean_title = (title or "").strip()
    if not clean_title:
        raise ValueError("title is required.")

    if os.name != "nt":
        return "Deleting desktop Outlook events is only supported on Windows."

    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return "pywin32 is required to delete Outlook events."

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        calendar = namespace.GetDefaultFolder(9)  # olFolderCalendar
        items = calendar.Items
        items.IncludeRecurrences = True
        items.Sort("[Start]")

        found = items.Find(f"[Subject] = '{clean_title}'")
        if not found:
            return f"Could not find an event named '{clean_title}' in your Outlook calendar."

        found.Delete()
        return f"Deleted event '{clean_title}' from your Outlook calendar."

    finally:
        pythoncom.CoUninitialize()
