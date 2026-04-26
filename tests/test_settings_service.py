import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core import settings_service


class SettingsServiceTests(unittest.TestCase):
    def test_save_api_key_uses_private_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "local_settings.json"

            with patch.object(settings_service, "_FILE", settings_path):
                settings_service.save_api_key("test-key")

                self.assertEqual(settings_service.get_api_key(), "test-key")
                self.assertTrue(settings_service.has_api_key())

                if os.name != "nt":
                    self.assertEqual(
                        stat.S_IMODE(settings_path.stat().st_mode),
                        0o600,
                    )
                    self.assertEqual(
                        stat.S_IMODE(settings_path.parent.stat().st_mode),
                        0o700,
                    )

    def test_remove_api_key_clears_saved_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "local_settings.json"

            with patch.object(settings_service, "_FILE", settings_path):
                settings_service.save_api_key("test-key")
                settings_service.remove_api_key()

                self.assertEqual(settings_service.get_api_key(), "")
                self.assertFalse(settings_service.has_api_key())

    def test_screen_viewing_setting_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "local_settings.json"

            with patch.object(settings_service, "_FILE", settings_path):
                self.assertFalse(settings_service.get_screen_viewing_enabled(default=False))

                settings_service.save_screen_viewing_enabled(True)
                self.assertTrue(settings_service.get_screen_viewing_enabled(default=False))

                settings_service.save_screen_viewing_enabled(False)
                self.assertFalse(settings_service.get_screen_viewing_enabled(default=True))

    def test_allowed_app_targets_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "local_settings.json"

            with patch.object(settings_service, "_FILE", settings_path):
                default = ["__web__", "Spotify"]
                self.assertEqual(settings_service.get_allowed_app_targets(default=default), default)

                settings_service.save_allowed_app_targets(["Spotify", "__web__", "spotify"])

                self.assertEqual(
                    settings_service.get_allowed_app_targets(default=[]),
                    ["Spotify", "__web__"],
                )


if __name__ == "__main__":
    unittest.main()
