# backend/core/chat_runtime.py
import uuid
from typing import Any

from google import genai
from google.genai import types

from backend.core.action_router import (
    build_calendar_action,
    build_confirmable_action,
    dispatch_intents,
    extract_calendar_intent,
    extract_clarify_intent,
    extract_confirmable_intent,
    validate_calendar_intent,
    validate_confirmable_intent,
)
from backend.core.confirmation import handle_pending_action
from backend.core.intent_classifier import classify
from backend.core.response_style import ask_quacky_confirmation, style_direct_output
from backend.features.open_app import (
    WEB_TARGET_ID,
    build_open_app_guidance,
    resolve_open_app_request,
)
from backend.features.timers import drain_due_alerts
from backend.personality.__init__ import (
    augment_with_context,
    is_preference_message,
    merge_system_instruction,
    update_memory,
)
from backend.tools import ALL_TOOLS


class ChatRuntime:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = str(api_key or "").strip()
        self.client = None
        self.model_name = model_name
        self.chats: dict[str, Any] = {}
        self._chat_configs: dict[str, dict[str, Any]] = {}
        self.memory: dict[str, dict] = {}
        self.open_app_confirmation_enabled = True
        self.app_control_suggestions_enabled = False
        self.timer_confirmation_enabled = True
        self.screen_viewing_enabled = False
        self._refresh_client()

    def _refresh_client(self) -> None:
        """Create or clear the Gemini client based on current API key state."""
        if not self.api_key:
            self.client = None
            return
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception:
            self.client = None

    def set_api_key(self, api_key: str) -> None:
        """Update the API key and rebind active chat sessions."""
        self.api_key = str(api_key or "").strip()
        self._refresh_client()
        for chat_id in list(self._chat_configs):
            self.chats[chat_id] = None

    def set_open_app_confirmation_enabled(self, enabled: bool) -> None:
        """Set whether open-app actions require explicit confirmation."""
        self.open_app_confirmation_enabled = bool(enabled)

    def set_app_control_suggestions_enabled(self, enabled: bool) -> None:
        """Set whether Quacky may suggest allowlist updates for blocked app requests."""
        self.app_control_suggestions_enabled = bool(enabled)

    def set_timer_confirmation_enabled(self, enabled: bool) -> None:
        """Set whether timer/alarm actions require explicit confirmation."""
        self.timer_confirmation_enabled = bool(enabled)

    def set_screen_viewing_enabled(self, enabled: bool) -> None:
        """Set whether screenshot context may be attached to chat requests."""
        self.screen_viewing_enabled = bool(enabled)

    def _create_remote_chat(self, system_instruction: str | None, model: str | None):
        if self.client is None:
            return None
        return self.client.chats.create(
            model=model or self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=ALL_TOOLS,
                temperature=0.2,
            ),
        )

    def _setup_guidance_message(self) -> str:
        """Return a direct setup guidance message when assistant requests are unavailable."""
        return (
            "Quacky is almost ready, but it needs a Gemini API key before I can respond. "
            "Open Settings > API Key, paste a key, click Save, then try again. "
            "Microphone access is requested when you start voice input, screen-sharing permission "
            "is requested when you enable Screen Viewing, and Outlook/calendar actions may require "
            "Outlook to be installed and signed in."
        )

    def _build_app_control_suggestion_action(self, intent: dict) -> dict | None:
        """Create a confirmation action to allow a blocked app target, then open it."""
        if not self.app_control_suggestions_enabled:
            return None

        app_name = str(intent.get("app") or "").strip()
        if not app_name:
            return None

        resolution = resolve_open_app_request(app_name)
        if not resolution.get("can_suggest_allow"):
            return None
        if bool(resolution.get("allowed")):
            return None

        target_id = str(resolution.get("target_id") or "").strip()
        if not target_id:
            return None

        display_name = str(resolution.get("display_name") or app_name).strip() or app_name
        target_summary = (
            "browser links"
            if target_id == WEB_TARGET_ID
            else f"'{display_name}'"
        )
        return {
            "kind": "app_control",
            "op": "allow_and_open",
            "args": {"target_id": target_id, "app_name": app_name},
            "summary": f"allow {target_summary} in app controls and open '{display_name}'",
        }

    def _preflight_open_app_intent(self, intent: dict) -> str | None:
        """Return an immediate user-facing message when an app request should not be confirmed yet."""
        app_name = str(intent.get("app") or "").strip()
        if not app_name:
            return None

        resolution = resolve_open_app_request(app_name)
        status = str(resolution.get("status") or "")

        if status in {"no_apps_configured", "not_found", "ambiguous"}:
            return build_open_app_guidance(app_name)

        if status in {"app", "direct_url"} and not bool(resolution.get("allowed")):
            if self.app_control_suggestions_enabled and bool(resolution.get("can_suggest_allow")):
                return None
            return build_open_app_guidance(app_name)

        return None

    @staticmethod
    def _attach_screen_context_note(message: str) -> str:
        text = (message or "").strip()
        note = (
            "The user also shared a screenshot of their current screen. "
            "Use it only when it helps answer the request."
        )
        return f"{text}\n\n{note}" if text else note

    @staticmethod
    def _send_chat_message(chat, message: str, screenshot_bytes: bytes | None, screenshot_mime_type: str) -> str:
        prompt = (message or "").strip()
        if not screenshot_bytes:
            try:
                return chat.send_message(prompt).text
            except Exception:
                return "Quacky hit a temporary model hiccup. Try that again in a moment."

        multimodal_prompt = ChatRuntime._attach_screen_context_note(prompt)
        mime_type = (screenshot_mime_type or "image/png").strip() or "image/png"

        try:
            response = chat.send_message(
                [
                    types.Part.from_text(text=multimodal_prompt),
                    types.Part.from_bytes(data=screenshot_bytes, mime_type=mime_type),
                ]
            )
            return response.text
        except Exception:
            fallback_prompt = (
                f"{prompt}\n\n"
                "A screenshot was available for this turn, but it could not be attached. "
                "Answer based on text only."
            ).strip()
            try:
                return chat.send_message(fallback_prompt).text
            except Exception:
                return "Quacky hit a temporary model hiccup while checking your screen. Try again in a moment."

    @staticmethod
    def _merge_due_alerts(text: str, due_alerts: list[str]) -> str:
        """Prepend due timer/alarm alerts to the normal assistant response."""
        if not due_alerts:
            return text
        alerts = "\n".join(f"- {line}" for line in due_alerts)
        prefix = f"Heads up, these timers/alarms just fired:\n{alerts}"
        if not text:
            return prefix
        return f"{prefix}\n\n{text}"

    def create_chat(self, system_instruction: str | None = None, model: str | None = None) -> str:
        merged_system = merge_system_instruction(system_instruction)
        chat_id = str(uuid.uuid4())
        self._chat_configs[chat_id] = {
            "system_instruction": merged_system,
            "model": model,
        }
        self.chats[chat_id] = self._create_remote_chat(merged_system, model)
        self.memory[chat_id] = {}
        return chat_id

    def get_history(self, chat_id: str) -> list[dict]:
        chat = self._get_chat(chat_id)
        if chat is None:
            return []
        history = []
        for msg in chat.get_history():
            text = "".join(part.text for part in msg.parts if getattr(part, "text", None))
            history.append({"role": msg.role, "text": text})
        return history

    def reset(self, chat_id: str) -> None:
        if chat_id not in self.chats:
            raise KeyError("chat not found")
        del self.chats[chat_id]
        self._chat_configs.pop(chat_id, None)
        self.memory.pop(chat_id, None)

    def handle_message(
        self,
        chat_id: str,
        message: str,
        screenshot_bytes: bytes | None = None,
        screenshot_mime_type: str = "image/png",
    ) -> str:
        chat = self._get_chat(chat_id)
        mem = self.memory.setdefault(chat_id, {})
        due_alerts = drain_due_alerts()
        screenshot_payload = screenshot_bytes if self.screen_viewing_enabled else None

        def finalize(response_text: str) -> str:
            return self._merge_due_alerts(response_text, due_alerts)

        if chat is None:
            update_memory(self.memory, chat_id, message)
            return finalize(self._setup_guidance_message())

        pending = mem.get("pending_action")
        if pending:
            return finalize(handle_pending_action(chat, self.memory, chat_id, message))

        intents = classify(message, self.client, self.model_name)
        lower_message = (message or "").lower()
        explicit_timer_request = any(
            marker in lower_message
            for marker in (
                "set timer",
                "set a timer",
                "set an alarm",
                "set a reminder",
                "remind me",
                "reminder for",
                "timer for",
                "alarm for",
                "remind",
                "cancel timer",
                "cancel alarm",
                "cancel reminder",
                "list timers",
                "list alarms",
                "list reminders",
                "what timers",
                "what alarms",
                "what reminders",
            )
        )
        if is_preference_message(message) and not explicit_timer_request:
            intents = [
                intent
                for intent in intents
                if (intent.get("intent") or "").lower()
                not in {"set_timer", "set_alarm", "cancel_timer"}
            ]
            if not intents:
                intents = [{"intent": "chat"}]

        clarify_intent = extract_clarify_intent(intents)
        if clarify_intent is not None:
            question = clarify_intent.get("question", "Could you clarify that for me?")
            update_memory(self.memory, chat_id, message)
            return finalize(chat.send_message(
                f"Rephrase this clarifying question in Quacky's voice, keep it short: {question}"
            ).text)

        calendar_intent = extract_calendar_intent(intents)
        if calendar_intent is not None:
            # Validate before building action
            validation_error = validate_calendar_intent(calendar_intent)
            if validation_error:
                update_memory(self.memory, chat_id, message)
                return finalize(chat.send_message(
                    f"Explain this validation error in Quacky's voice, friendly but clear: {validation_error}"
                ).text)
            
            action = build_calendar_action(calendar_intent)
            if action is not None:
                action["user_message"] = message
                mem["pending_action"] = action
                update_memory(self.memory, chat_id, message)
                return finalize(ask_quacky_confirmation(chat, message, action["summary"]))

        for intent in intents:
            if (intent.get("intent") or "").lower() != "open_app":
                continue
            guidance = self._preflight_open_app_intent(intent)
            if guidance is not None:
                update_memory(self.memory, chat_id, message)
                return finalize(style_direct_output(chat, message, guidance))
            action = self._build_app_control_suggestion_action(intent)
            if action is None:
                continue
            action["user_message"] = message
            mem["pending_action"] = action
            update_memory(self.memory, chat_id, message)
            return finalize(ask_quacky_confirmation(chat, message, action["summary"]))

        confirmable_candidates: list[dict] = []
        for intent in intents:
            kind = (intent.get("intent") or "").lower()
            if kind == "open_app" and not self.open_app_confirmation_enabled:
                continue
            if kind in {"set_timer", "set_alarm", "set_reminder", "cancel_timer"} and not self.timer_confirmation_enabled:
                continue
            confirmable_candidates.append(intent)

        confirmable_intent = extract_confirmable_intent(confirmable_candidates)
        if confirmable_intent is not None:
            validation_error = validate_confirmable_intent(confirmable_intent)
            if validation_error:
                update_memory(self.memory, chat_id, message)
                return finalize(chat.send_message(
                    f"Explain this validation error in Quacky's voice, friendly but clear: {validation_error}"
                ).text)

            action = build_confirmable_action(confirmable_intent)
            if action is not None:
                action["user_message"] = message
                mem["pending_action"] = action
                update_memory(self.memory, chat_id, message)
                return finalize(ask_quacky_confirmation(chat, message, action["summary"]))

        direct_result = dispatch_intents(intents)
        if direct_result is not None:
            update_memory(self.memory, chat_id, message)
            return finalize(style_direct_output(chat, message, direct_result))

        augmented = augment_with_context(self.memory, chat_id, message)
        update_memory(self.memory, chat_id, message)
        return finalize(
            self._send_chat_message(
                chat,
                augmented,
                screenshot_payload,
                screenshot_mime_type,
            )
        )

    def _get_chat(self, chat_id: str):
        if not chat_id or chat_id not in self.chats:
            raise KeyError("chat not found")
        if self.chats[chat_id] is None and self.client is not None:
            config = self._chat_configs.get(chat_id, {})
            self.chats[chat_id] = self._create_remote_chat(
                system_instruction=config.get("system_instruction"),
                model=config.get("model"),
            )
        return self.chats[chat_id]
