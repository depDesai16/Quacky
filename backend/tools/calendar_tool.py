"""
Calendar tool wrappers for Quacky.
"""

import re

from backend.core.activity_store import add_calendar_event
from backend.features.calendar.calendar_feature import (
    create_outlook_event,
    update_outlook_event,
    delete_outlook_event,
)


_ISO_SPAN_PATTERN = re.compile(
    r"\bfrom\s+(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+to\s+"
    r"(?P<end>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",
    flags=re.IGNORECASE,
)
_ISO_DASH_SPAN_PATTERN = re.compile(
    r"\bto\s+(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+[–-]\s+"
    r"(?P<end>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",
    flags=re.IGNORECASE,
)


def _looks_successful(result: str) -> bool:
    text = (result or "").strip().lower()
    if not text:
        return False
    if text.startswith("could not find"):
        return False
    if text.startswith("updating desktop outlook events is only supported"):
        return False
    if text.startswith("deleting desktop outlook events is only supported"):
        return False
    if text.startswith("pywin32 is required"):
        return False
    return True


def _extract_times_from_result(result: str) -> tuple[str, str]:
    text = result or ""
    match = _ISO_SPAN_PATTERN.search(text)
    if match:
        return match.group("start"), match.group("end")
    match = _ISO_DASH_SPAN_PATTERN.search(text)
    if match:
        return match.group("start"), match.group("end")
    return "", ""

def add_outlook_event(
    title: str,
    start_time: str,
    end_time: str = "",
    duration_minutes: int = 60,
    location: str = "",
    details: str = "",
) -> str:
    """
    Add a new event to the Outlook calendar.

    title: name of the event
    start_time: natural language ok - "tomorrow 3pm", "next Monday at 10am"
    end_time: optional, natural language ok
    duration_minutes: optional, default 60
    location: optional
    details: optional
    """
    result = create_outlook_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        location=location,
        details=details,
    )
    parsed_start, parsed_end = _extract_times_from_result(result)
    add_calendar_event(
        action="create",
        title=title,
        start_time=parsed_start or start_time,
        end_time=parsed_end or end_time,
        location=location,
        details=details,
        status="ok" if _looks_successful(result) else "error",
        result=result,
    )
    return result

def update_outlook_event_time(
    title: str,
    new_start_time: str,
    new_end_time: str = "",
    new_duration_minutes: int = 0,
) -> str:
    """
    Update an existing Outlook calendar event's time by its title.

    title: exact name of the event to update
    new_start_time: natural language ok - "tomorrow 3pm", "Friday 10am"
    new_end_time: optional
    new_duration_minutes: optional, keeps original duration if omitted
    """
    result = update_outlook_event(
        title=title,
        new_start_time=new_start_time,
        new_end_time=new_end_time,
        new_duration_minutes=new_duration_minutes,
    )
    parsed_start, parsed_end = _extract_times_from_result(result)
    add_calendar_event(
        action="update",
        title=title,
        start_time=parsed_start or new_start_time,
        end_time=parsed_end or new_end_time,
        status="ok" if _looks_successful(result) else "error",
        result=result,
    )
    return result

def delete_outlook_event_by_title(title: str) -> str:
    """
    Delete an existing Outlook calendar event by its title.

    title: exact name of the event to delete
    """
    result = delete_outlook_event(title=title)
    add_calendar_event(
        action="delete",
        title=title,
        status="ok" if _looks_successful(result) else "error",
        result=result,
    )
    return result
