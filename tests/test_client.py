import base64
import unittest
from unittest.mock import patch
from urllib.error import URLError

from backend.client import QuackyClient


class QuackyClientTests(unittest.TestCase):
    def test_client_rejects_non_http_base_url(self):
        with self.assertRaises(ValueError):
            QuackyClient(base_url="file:///tmp/quacky")

    def test_send_message_includes_screenshot_payload_when_provided(self):
        client = QuackyClient()

        with patch.object(client, "_post", return_value={"ok": True}) as post:
            client.send_message(
                "chat-1",
                "what is on my screen?",
                screenshot_base64="abc123",
                screenshot_mime_type="image/png",
            )

        post.assert_called_once_with(
            "/chat/message",
            {
                "chat_id": "chat-1",
                "message": "what is on my screen?",
                "screenshot_base64": "abc123",
                "screenshot_mime_type": "image/png",
            },
        )

    def test_decode_audio_bytes_returns_bytes_for_valid_payload(self):
        audio = b"quack"
        payload = {"audio_base64": base64.b64encode(audio).decode("ascii")}

        self.assertEqual(QuackyClient.decode_audio_bytes(payload), audio)

    def test_decode_audio_bytes_returns_none_for_invalid_payload(self):
        self.assertIsNone(QuackyClient.decode_audio_bytes({"audio_base64": "not-base64"}))

    def test_post_returns_error_payload_on_url_error(self):
        client = QuackyClient()

        with patch("urllib.request.urlopen", side_effect=URLError("offline")):
            response = client._post("/chat/start", {})

        self.assertIn("error", response)
        self.assertIn("offline", response["error"])


if __name__ == "__main__":
    unittest.main()
