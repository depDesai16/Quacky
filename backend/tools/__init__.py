"""
Tool registry for Quacky.
"""

from .weather_tool import get_weather
from .holiday_tool import get_holidays
from .calendar_tool import (
    add_outlook_event,
    update_outlook_event_time,
    delete_outlook_event_by_title,
)
from .app_tool import open_app
from .email_tool import send_email
from .memory_tool import (
    remember_memory,
    recall_memory,
    forget_memory,
    add_task_memory,
    list_task_memory,
    complete_task_memory,
)

ALL_TOOLS = [
    get_weather,
    get_holidays,
    add_outlook_event,
    update_outlook_event_time,
    delete_outlook_event_by_title,
    open_app,
    send_email,
    remember_memory,
    recall_memory,
    forget_memory,
    add_task_memory,
    list_task_memory,
    complete_task_memory,
]

__all__ = [
    "get_weather",
    "get_holidays",
    "add_outlook_event",
    "update_outlook_event_time",
    "delete_outlook_event_by_title",
    "open_app",
    "send_email",
    "remember_memory",
    "recall_memory",
    "forget_memory",
    "add_task_memory",
    "list_task_memory",
    "complete_task_memory",
    "ALL_TOOLS",
]
