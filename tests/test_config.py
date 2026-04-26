import unittest
from unittest.mock import patch

from backend import config


class ConfigTests(unittest.TestCase):
    def test_get_settings_uses_default_values(self):
        env = {"GEMINI_API_KEY": "test-key"}

        with patch.object(config, "load_dotenv", lambda *a, **kw: None):
            with patch.dict("os.environ", env, clear=True):
                settings = config.get_settings()

        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.model_name, "gemini-2.5-flash")
        self.assertEqual(settings.port, 8000)
        self.assertFalse(settings.tts_default_enabled)

    def test_get_settings_supports_google_api_key(self):
        env = {"GOOGLE_API_KEY": "google-key", "PORT": "9000", "TTS_DEFAULT_ENABLED": "true"}

        with patch.object(config, "load_dotenv", lambda *a, **kw: None):
            with patch.dict("os.environ", env, clear=True):
                settings = config.get_settings()

        self.assertEqual(settings.api_key, "google-key")
        self.assertEqual(settings.port, 9000)
        self.assertTrue(settings.tts_default_enabled)

    def test_get_settings_allows_missing_api_key_for_setup_guidance(self):
        with patch.object(config, "load_dotenv", lambda *a, **kw: None):
            with patch.dict("os.environ", {}, clear=True):
                settings = config.get_settings()

        self.assertEqual(settings.api_key, "")


if __name__ == "__main__":
    unittest.main()
