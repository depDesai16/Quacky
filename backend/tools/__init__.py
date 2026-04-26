"""
Tool registry for Quacky.
"""

from .app_tool import open_app
from .calendar_tool import (
    add_outlook_event,
    delete_outlook_event_by_title,
    update_outlook_event_time,
)
from .email_tool import send_email
from .holiday_tool import get_holidays
from .memory_tool import clear_memory, forget_memory_item, list_memory
from .timer_tool import cancel_timer, list_timers, set_alarm, set_reminder, set_timer
from .weather_tool import get_weather

ALL_TOOLS = [
    get_weather,
    get_holidays,
    add_outlook_event,
    update_outlook_event_time,
    delete_outlook_event_by_title,
    open_app,
    send_email,
    set_timer,
    set_alarm,
    set_reminder,
    list_timers,
    cancel_timer,
    list_memory,
    forget_memory_item,
    clear_memory,
]

__all__ = [
    "get_weather",
    "get_holidays",
    "add_outlook_event",
    "update_outlook_event_time",
    "delete_outlook_event_by_title",
    "open_app",
    "send_email",
    "set_timer",
    "set_alarm",
    "set_reminder",
    "list_timers",
    "cancel_timer",
    "list_memory",
    "forget_memory_item",
    "clear_memory",
    "ALL_TOOLS",
]
