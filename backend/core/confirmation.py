# backend/core/confirmation.py
from backend.personality.__init__ import update_memory
from backend.tools import (
    add_outlook_event,
    update_outlook_event_time,
    delete_outlook_event_by_title,
    open_app,
    send_email,
    set_timer,
    set_alarm,
    cancel_timer,
    clear_memory,
)
from backend.core.response_style import style_direct_output

YES = {"yes","y","yeah","yep","ok","okay","confirm","sure","go ahead","do it","please"}
NO  = {"no","n","nope","nah","cancel","stop","don't","do not","nevermind","never mind"}

def is_yes(text: str) -> bool:
    return (text or "").strip().lower() in YES

def is_no(text: str) -> bool:
    return (text or "").strip().lower() in NO


def _execute_pending_action(pending: dict) -> str:
    """Execute the pending action once the user confirms."""
    kind = (pending.get("kind") or "").lower()
    op = (pending.get("op") or "").lower()
    args = pending.get("args", {}) or {}

    if kind == "calendar":
        if op == "create":
            return add_outlook_event(**args)
        if op == "update":
            return update_outlook_event_time(**args)
        if op == "delete":
            return delete_outlook_event_by_title(**args)
        return "Unknown calendar operation."

    if kind == "open_app":
        return open_app(args.get("app_name", ""))

    if kind == "send_email":
        return send_email(
            email_address=args.get("email_address", ""),
            subject=args.get("subject", ""),
            body=args.get("body", ""),
        )

    if kind == "timer":
        if op == "set_timer":
            try:
                duration = int(args.get("duration_seconds") or 0)
            except (TypeError, ValueError):
                duration = 0
            return set_timer(duration_seconds=duration, label=args.get("label", ""))
        if op == "set_alarm":
            return set_alarm(
                alarm_time=args.get("alarm_time", ""),
                label=args.get("label", ""),
            )
        if op == "cancel":
            return cancel_timer(timer_ref=args.get("timer_ref", ""))
        return "Unknown timer operation."

    if kind == "memory":
        if op == "clear_all":
            return clear_memory(scope=args.get("scope", "all"))
        return "Unknown memory operation."

    return "Unknown pending operation."


def handle_pending_action(chat, memory: dict, chat_id: str, user_reply: str) -> str:
    """
    Handles the user's reply when there is a pending action awaiting confirmation.
    """
    pending = (memory.get(chat_id, {}) or {}).get("pending_action") or {}
    original_user_message = pending.get("user_message", "") or ""

    if is_yes(user_reply):
        try:
            result = _execute_pending_action(pending)
        except Exception as exc:
            result = f"[Error] {exc}"

        memory[chat_id].pop("pending_action", None)
        update_memory(memory, chat_id, original_user_message or user_reply)
        return style_direct_output(chat, original_user_message or user_reply, result)

    if is_no(user_reply):
        memory[chat_id].pop("pending_action", None)
        update_memory(memory, chat_id, original_user_message or user_reply)
        return chat.send_message(
            "User declined the pending action. Reply in Quacky's voice, short and friendly."
        ).text

    return chat.send_message(
        "There is a pending action awaiting confirmation. Ask the user to reply yes or no, in Quacky's voice."
    ).text


def handle_pending_calendar(chat, memory: dict, chat_id: str, user_reply: str) -> str:
    """
    Backwards-compatible alias for older call sites.
    """
    return handle_pending_action(chat, memory, chat_id, user_reply)
