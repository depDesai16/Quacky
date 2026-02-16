"""
Calendar tool wrappers for Quacky.
"""

from backend.features.calendar.calendar_feature import (
    create_outlook_event,
    update_outlook_event,
    delete_outlook_event,
)

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
    return create_outlook_event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        location=location,
        details=details,
    )

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
    return update_outlook_event(
        title=title,
        new_start_time=new_start_time,
        new_end_time=new_end_time,
        new_duration_minutes=new_duration_minutes,
    )

def delete_outlook_event_by_title(title: str) -> str:
    """
    Delete an existing Outlook calendar event by its title.

    title: exact name of the event to delete
    """
    return delete_outlook_event(title=title)