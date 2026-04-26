import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch


def _load_chat_runtime_module():
    google_stub = types.ModuleType("google")
    genai_stub = types.ModuleType("google.genai")
    genai_stub.Client = Mock()
    types_stub = types.ModuleType("google.genai.types")
    types_stub.GenerateContentConfig = Mock()
    types_stub.Part = Mock()
    genai_stub.types = types_stub
    google_stub.genai = genai_stub

    action_router_stub = types.ModuleType("backend.core.action_router")
    action_router_stub.build_calendar_action = Mock(return_value=None)
    action_router_stub.build_confirmable_action = Mock(return_value=None)
    action_router_stub.dispatch_intents = Mock(return_value=None)
    action_router_stub.extract_calendar_intent = Mock(return_value=None)
    action_router_stub.extract_clarify_intent = Mock(return_value=None)
    action_router_stub.extract_confirmable_intent = Mock(return_value=None)
    action_router_stub.validate_calendar_intent = Mock(return_value=None)
    action_router_stub.validate_confirmable_intent = Mock(return_value=None)

    confirmation_stub = types.ModuleType("backend.core.confirmation")
    confirmation_stub.handle_pending_action = Mock(return_value="pending")

    intent_classifier_stub = types.ModuleType("backend.core.intent_classifier")
    intent_classifier_stub.classify = Mock(return_value=[{"intent": "chat"}])

    response_style_stub = types.ModuleType("backend.core.response_style")
    response_style_stub.ask_quacky_confirmation = Mock(return_value="confirm")
    response_style_stub.style_direct_output = Mock(return_value="styled")

    timers_stub = types.ModuleType("backend.features.timers")
    timers_stub.drain_due_alerts = Mock(return_value=[])

    open_app_stub = types.ModuleType("backend.features.open_app")
    open_app_stub.WEB_TARGET_ID = "__web__"
    open_app_stub.resolve_open_app_request = Mock(
        return_value={
            "status": "app",
            "requested_name": "spotify",
            "display_name": "Spotify",
            "target_id": "Spotify",
            "allowed": False,
            "can_suggest_allow": True,
        }
    )

    personality_stub = types.ModuleType("backend.personality.__init__")
    personality_stub.augment_with_context = Mock(side_effect=lambda memory, chat_id, message: message)
    personality_stub.is_preference_message = Mock(return_value=False)
    personality_stub.merge_system_instruction = Mock(side_effect=lambda text: text or "")
    personality_stub.update_memory = Mock()

    tools_stub = types.ModuleType("backend.tools")
    tools_stub.ALL_TOOLS = []

    with patch.dict(
        sys.modules,
        {
            "google": google_stub,
            "google.genai": genai_stub,
            "google.genai.types": types_stub,
            "backend.core.action_router": action_router_stub,
            "backend.core.confirmation": confirmation_stub,
            "backend.core.intent_classifier": intent_classifier_stub,
            "backend.core.response_style": response_style_stub,
            "backend.features.timers": timers_stub,
            "backend.features.open_app": open_app_stub,
            "backend.personality.__init__": personality_stub,
            "backend.tools": tools_stub,
        },
    ):
        sys.modules.pop("backend.core.chat_runtime", None)
        module = importlib.import_module("backend.core.chat_runtime")
    return module, intent_classifier_stub, open_app_stub, response_style_stub


class ChatRuntimeTests(unittest.TestCase):
    def test_handle_message_without_api_key_returns_setup_guidance(self):
        module, _intent_classifier_stub, _open_app_stub, _response_style_stub = _load_chat_runtime_module()
        runtime = module.ChatRuntime(api_key="", model_name="gemini-2.5-flash")
        chat_id = runtime.create_chat()

        result = runtime.handle_message(chat_id, "hello")

        self.assertIn("needs a Gemini API key", result)
        self.assertIn("Settings > API Key", result)

    def test_blocked_open_app_can_become_allowlist_confirmation(self):
        module, intent_classifier_stub, _open_app_stub, response_style_stub = _load_chat_runtime_module()
        runtime = module.ChatRuntime(api_key="test-key", model_name="gemini-2.5-flash")
        runtime.set_app_control_suggestions_enabled(True)
        chat = Mock()
        chat.send_message.return_value.text = "confirm app control"
        runtime.chats["chat-1"] = chat
        runtime._chat_configs["chat-1"] = {"system_instruction": "", "model": None}
        intent_classifier_stub.classify.return_value = [{"intent": "open_app", "app": "spotify"}]
        response_style_stub.ask_quacky_confirmation.return_value = "confirm app control"

        result = runtime.handle_message("chat-1", "open spotify")

        self.assertEqual(result, "confirm app control")
        pending = runtime.memory["chat-1"]["pending_action"]
        self.assertEqual(pending["kind"], "app_control")
        self.assertEqual(pending["op"], "allow_and_open")


if __name__ == "__main__":
    unittest.main()
