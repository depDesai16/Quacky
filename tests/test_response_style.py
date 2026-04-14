import unittest
from unittest.mock import Mock

from backend.core.response_style import ask_quacky_confirmation, style_direct_output


class ResponseStyleTests(unittest.TestCase):
    def test_style_direct_output_falls_back_when_styling_call_fails(self):
        chat = Mock()
        chat.send_message.side_effect = RuntimeError("model unavailable")

        result = style_direct_output(chat, "open spotify", "Opened Spotify.")

        self.assertEqual(result, "Opened Spotify.")

    def test_confirmation_falls_back_when_styling_call_fails(self):
        chat = Mock()
        chat.send_message.side_effect = RuntimeError("model unavailable")

        result = ask_quacky_confirmation(chat, "open spotify", "open 'spotify'")

        self.assertEqual(result, "Please confirm the following action: open 'spotify'")


if __name__ == "__main__":
    unittest.main()
