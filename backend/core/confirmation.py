# backend/core/confirmation.py
from backend.personality.__init__ import update_memory
from backend.tools import add_outlook_event, update_outlook_event_time, delete_outlook_event_by_title
from backend.core.response_style import style_direct_output

YES = {"yes","y","yeah","yep","ok","okay","confirm","sure","go ahead","do it","please"}
NO  = {"no","n","nope","nah","cancel","stop","don't","do not","nevermind","never mind"}

def is_yes(text: str) -> bool:
    """Return True when the user reply is an affirmative confirmation token."""
    return (text or "").strip().lower() in YES

def is_no(text: str) -> bool:
    """Return True when the user reply is a negative/cancel token."""
    return (text or "").strip().lower() in NO


def handle_pending_calendar(chat, memory: dict, chat_id: str, user_reply: str) -> str:
    """
    Handles the user's reply when there is a pending calendar action awaiting confirmation.
    """
    pending = (memory.get(chat_id, {}) or {}).get("pending_action") or {}
    original_user_message = pending.get("user_message", "") or ""

    if is_yes(user_reply):
        op = pending.get("op")
        args = pending.get("args", {})

        try:
            if op == "create":
                result = add_outlook_event(**args)
            elif op == "update":
                result = update_outlook_event_time(**args)
            elif op == "delete":
                result = delete_outlook_event_by_title(**args)
            else:
                result = "Unknown calendar operation."
        except Exception as exc:
            result = f"[Error] {exc}"

        memory[chat_id].pop("pending_action", None)
        update_memory(memory, chat_id, original_user_message or user_reply)
        return style_direct_output(chat, original_user_message or user_reply, result)

    if is_no(user_reply):
        memory[chat_id].pop("pending_action", None)
        update_memory(memory, chat_id, original_user_message or user_reply)
        return chat.send_message(
            "User declined the pending calendar action. Reply in Quacky's voice, short and friendly."
        ).text

    return chat.send_message(
        "There is a pending calendar action awaiting confirmation. Ask the user to reply yes or no, in Quacky's voice."
    ).text
