# backend/core/chat_runtime.py
import uuid
from typing import Any

from google import genai
from google.genai import types

from backend.personality.__init__ import merge_system_instruction, augment_with_context, update_memory
from backend.tools import ALL_TOOLS
from backend.core.intent_classifier import classify
from backend.core.action_router import (
    dispatch_intents,
    extract_calendar_intent,
    extract_clarify_intent,
    validate_calendar_intent,
    build_calendar_action,
)
from backend.core.response_style import ask_quacky_confirmation, style_direct_output
from backend.core.confirmation import handle_pending_calendar
from backend.core.session_memory import SessionMemoryStore


class ChatRuntime:
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.chats: dict[str, Any] = {}
        self.memory: dict[str, dict] = {}
        self.memory_store = SessionMemoryStore()

    def create_chat(self, system_instruction: str | None = None, model: str | None = None) -> str:
        merged_system = merge_system_instruction(system_instruction)
        chat = self.client.chats.create(
            model=model or self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=merged_system,
                tools=ALL_TOOLS,
                temperature=0.2,
            ),
        )
        chat_id = str(uuid.uuid4())
        self.chats[chat_id] = chat
        self.memory[chat_id] = self.memory_store.get_session(chat_id)
        return chat_id

    def get_history(self, chat_id: str) -> list[dict]:
        chat = self._get_chat(chat_id)
        history = []
        for msg in chat.get_history():
            text = "".join(part.text for part in msg.parts if getattr(part, "text", None))
            history.append({"role": msg.role, "text": text})
        return history

    def reset(self, chat_id: str) -> None:
        if chat_id not in self.chats:
            raise KeyError("chat not found")
        del self.chats[chat_id]
        self.memory.pop(chat_id, None)
        self.memory_store.delete_session(chat_id)

    def handle_message(self, chat_id: str, message: str) -> str:
        chat = self._get_chat(chat_id)
        mem = self.memory.setdefault(chat_id, self.memory_store.get_session(chat_id))

        def _persist_and_return(text: str) -> str:
            self.memory_store.save_session(chat_id, mem)
            return text

        pending = mem.get("pending_action")
        if pending and pending.get("kind") == "calendar":
            return _persist_and_return(handle_pending_calendar(chat, self.memory, chat_id, message))

        intents = classify(message, self.client, self.model_name)

        clarify_intent = extract_clarify_intent(intents)
        if clarify_intent is not None:
            question = clarify_intent.get("question", "Could you clarify that for me?")
            update_memory(self.memory, chat_id, message)
            return _persist_and_return(chat.send_message(
                f"Rephrase this clarifying question in Quacky's voice, keep it short: {question}"
            ).text)

        calendar_intent = extract_calendar_intent(intents)
        if calendar_intent is not None:
            # Validate before building action
            validation_error = validate_calendar_intent(calendar_intent)
            if validation_error:
                update_memory(self.memory, chat_id, message)
                return _persist_and_return(chat.send_message(
                    f"Explain this validation error in Quacky's voice, friendly but clear: {validation_error}"
                ).text)
            
            action = build_calendar_action(calendar_intent)
            if action is not None:
                action["user_message"] = message
                mem["pending_action"] = action
                update_memory(self.memory, chat_id, message)
                return _persist_and_return(ask_quacky_confirmation(chat, message, action["summary"]))

        direct_result = dispatch_intents(intents)
        if direct_result is not None:
            update_memory(self.memory, chat_id, message)
            return _persist_and_return(style_direct_output(chat, message, direct_result))

        augmented = augment_with_context(self.memory, chat_id, message)
        augmented = (
            f"{augmented}\n\n"
            f"[Internal tool hint: current_chat_id={chat_id}. "
            "If memory tools are used, pass this value as chat_id.]"
        )
        update_memory(self.memory, chat_id, message)
        return _persist_and_return(chat.send_message(augmented).text)

    def _get_chat(self, chat_id: str):
        if not chat_id or chat_id not in self.chats:
            raise KeyError("chat not found")
        return self.chats[chat_id]
