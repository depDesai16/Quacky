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
            "backend.personality.__init__": personality_stub,
            "backend.tools": tools_stub,
        },
    ):
        sys.modules.pop("backend.core.chat_runtime", None)
        module = importlib.import_module("backend.core.chat_runtime")
    return module


class ChatRuntimeTests(unittest.TestCase):
    def test_handle_message_without_api_key_returns_setup_guidance(self):
        module = _load_chat_runtime_module()
        runtime = module.ChatRuntime(api_key="", model_name="gemini-2.5-flash")
        chat_id = runtime.create_chat()

        result = runtime.handle_message(chat_id, "hello")

        self.assertIn("needs a Gemini API key", result)
        self.assertIn("Settings > API Key", result)


if __name__ == "__main__":
    unittest.main()
