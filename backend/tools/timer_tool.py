"""Timer/alarm tool wrappers for Quacky."""

from backend.features.timers import (
    cancel_timer as cancel_timer_feature,
)
from backend.features.timers import (
    list_timers as list_timers_feature,
)
from backend.features.timers import (
    set_alarm as set_alarm_feature,
)
from backend.features.timers import (
    set_reminder as set_reminder_feature,
)
from backend.features.timers import (
    set_timer as set_timer_feature,
)


def set_timer(duration_seconds: int, label: str = "") -> str:
    """
    Set an in-house timer for a number of seconds.
    """
    return set_timer_feature(duration_seconds=duration_seconds, label=label)


def set_alarm(alarm_time: str, label: str = "") -> str:
    """
    Set an in-house alarm at a specific time.
    """
    return set_alarm_feature(alarm_time=alarm_time, label=label)


def set_reminder(reminder_time: str, note: str) -> str:
    """
    Set an in-house reminder at a specific time with reminder text.
    """
    return set_reminder_feature(reminder_time=reminder_time, note=note)


def list_timers() -> str:
    """
    List active in-house timers and alarms.
    """
    return list_timers_feature()


def cancel_timer(timer_ref: str) -> str:
    """
    Cancel an active in-house timer/alarm using an id or label.
    """
    return cancel_timer_feature(timer_ref=timer_ref)
