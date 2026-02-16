# backend/core/chat_runtime.py
import uuid
from typing import Any

from google import genai
from google.genai import types

from backend.personality.__init__ import merge_system_instruction, augment_with_context, update_memory
from backend.tools import ALL_TOOLS
from backend.core.intent_classifier import classify
from backend.core.action_router import dispatch_intents, extract_calendar_intent, build_calendar_action
from backend.core.response_style import ask_quacky_confirmation, style_direct_output
from backend.core.confirmation import handle_pending_calendar


class ChatRuntime:
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.chats: dict[str, Any] = {}
        self.memory: dict[str, dict] = {}

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
        self.memory[chat_id] = {}
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

    def handle_message(self, chat_id: str, message: str) -> str:
        chat = self._get_chat(chat_id)
        mem = self.memory.setdefault(chat_id, {})

        # ── 1. Pending calendar confirmation ─────────────────────────────────
        # Handle yes/no replies BEFORE classifying so "yes" stays as confirmation
        pending = mem.get("pending_action")
        if pending and pending.get("kind") == "calendar":
            return handle_pending_calendar(chat, self.memory, chat_id, message)

        # ── 2. Classify intent ────────────────────────────────────────────────
        intents = classify(message, self.client, self.model_name)

        # ── 3. Calendar → confirmation flow ──────────────────────────────────
        calendar_intent = extract_calendar_intent(intents)
        if calendar_intent is not None:
            action = build_calendar_action(calendar_intent)
            if action is not None:
                action["user_message"] = message
                mem["pending_action"] = action
                update_memory(self.memory, chat_id, message)
                return ask_quacky_confirmation(chat, message, action["summary"])
            # Missing required fields - fall through to chat

        # ── 4. Weather / holiday / open_app → dispatch ────────────────────────
        direct_result = dispatch_intents(intents)
        if direct_result is not None:
            update_memory(self.memory, chat_id, message)
            return style_direct_output(chat, message, direct_result)

        # ── 5. Chat fallback ──────────────────────────────────────────────────
        augmented = augment_with_context(self.memory, chat_id, message)
        update_memory(self.memory, chat_id, message)
        return chat.send_message(augmented).text

    def _get_chat(self, chat_id: str):
        if not chat_id or chat_id not in self.chats:
            raise KeyError("chat not found")
        return self.chats[chat_id]