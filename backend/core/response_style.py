# backend/core/response_style.py
from google.genai import errors as genai_errors


def style_direct_output(chat, user_message: str, tool_result: str) -> str:
    """
    Rephrase deterministic/tool output using the same chat (and therefore system prompt).
    Does NOT re-run tools; only rewrites the output.
    """
    prompt = (
        "Rewrite the following tool result in Quacky's voice using the system instructions.\n"
        "Keep the factual details exactly the same.\n"
        "Be concise.\n\n"
        f"User asked: {user_message}\n\n"
        f"Tool result:\n{tool_result}"
    )
    try:
        return chat.send_message(prompt).text
    except genai_errors.ClientError:
        return tool_result


def ask_quacky_confirmation(chat, user_message: str, action_summary: str) -> str:
    prompt = (
        "Ask the user to confirm the action below in Quacky's voice using the system instructions.\n"
        "Be short, playful, and clear.\n"
        "End with a direct yes/no question.\n\n"
        f"User said: {user_message}\n"
        f"Action: {action_summary}\n"
    )
    try:
        return chat.send_message(prompt).text
    except genai_errors.ClientError:
        return f"Please confirm the following action: {action_summary}"
