import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch


def _load_confirmation_module():
    tools_stub = types.ModuleType("backend.tools")
    tools_stub.add_outlook_event = Mock(return_value="calendar created")
    tools_stub.update_outlook_event_time = Mock(return_value="calendar updated")
    tools_stub.delete_outlook_event_by_title = Mock(return_value="calendar deleted")
    tools_stub.open_app = Mock(return_value="app opened")
    tools_stub.send_email = Mock(return_value="email sent")
    tools_stub.set_timer = Mock(return_value="timer set")
    tools_stub.set_alarm = Mock(return_value="alarm set")
    tools_stub.set_reminder = Mock(return_value="reminder set")
    tools_stub.cancel_timer = Mock(return_value="timer canceled")
    tools_stub.clear_memory = Mock(return_value="memory cleared")

    personality_stub = types.ModuleType("backend.personality.__init__")
    personality_stub.update_memory = Mock()

    response_style_stub = types.ModuleType("backend.core.response_style")
    response_style_stub.style_direct_output = Mock(return_value="styled output")

    with patch.dict(
        sys.modules,
        {
            "backend.tools": tools_stub,
            "backend.personality.__init__": personality_stub,
            "backend.core.response_style": response_style_stub,
        },
    ):
        sys.modules.pop("backend.core.confirmation", None)
        module = importlib.import_module("backend.core.confirmation")

    return module, tools_stub, personality_stub, response_style_stub


class ConfirmationTests(unittest.TestCase):
    def test_handle_pending_action_executes_timer_on_yes(self):
        confirmation, tools_stub, personality_stub, response_style_stub = _load_confirmation_module()
        chat = Mock()
        memory = {
            "chat-1": {
                "pending_action": {
                    "kind": "timer",
                    "op": "set_timer",
                    "args": {"duration_seconds": "90", "label": "focus"},
                    "user_message": "set a focus timer",
                }
            }
        }

        result = confirmation.handle_pending_action(chat, memory, "chat-1", "yes")

        tools_stub.set_timer.assert_called_once_with(duration_seconds=90, label="focus")
        personality_stub.update_memory.assert_called_once_with(memory, "chat-1", "set a focus timer")
        response_style_stub.style_direct_output.assert_called_once_with(chat, "set a focus timer", "timer set")
        self.assertEqual(memory["chat-1"], {})
        self.assertEqual(result, "styled output")

    def test_handle_pending_action_declines_on_no(self):
        confirmation, _tools_stub, personality_stub, _response_style_stub = _load_confirmation_module()
        chat = Mock()
        chat.send_message.return_value.text = "declined reply"
        memory = {
            "chat-1": {
                "pending_action": {
                    "kind": "open_app",
                    "args": {"app_name": "spotify"},
                    "user_message": "open spotify",
                }
            }
        }

        result = confirmation.handle_pending_action(chat, memory, "chat-1", "no")

        personality_stub.update_memory.assert_called_once_with(memory, "chat-1", "open spotify")
        chat.send_message.assert_called_once()
        self.assertEqual(memory["chat-1"], {})
        self.assertEqual(result, "declined reply")

    def test_handle_pending_action_prompts_again_for_non_confirmation_reply(self):
        confirmation, tools_stub, personality_stub, response_style_stub = _load_confirmation_module()
        chat = Mock()
        chat.send_message.return_value.text = "please answer yes or no"
        memory = {"chat-1": {"pending_action": {"kind": "send_email"}}}

        result = confirmation.handle_pending_action(chat, memory, "chat-1", "maybe")

        tools_stub.send_email.assert_not_called()
        personality_stub.update_memory.assert_not_called()
        response_style_stub.style_direct_output.assert_not_called()
        self.assertEqual(result, "please answer yes or no")


if __name__ == "__main__":
    unittest.main()
