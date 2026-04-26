import unittest
from unittest.mock import patch

from backend.features.open_app import open_app_feature


class OpenAppSecurityTests(unittest.TestCase):
    def test_windows_launch_avoids_shell_true(self):
        command = '"C:/Program Files/App/app.exe" --flag'

        with patch.object(open_app_feature.sys, "platform", "win32"):
            with patch.object(open_app_feature.subprocess, "Popen") as popen:
                open_app_feature._launch_command(command)

        popen.assert_called_once_with(command)

    def test_open_app_blocks_when_target_disallowed(self):
        app = open_app_feature.AppEntry(
            name="Spotify",
            command="spotify",
            os_commands={},
            aliases=(),
        )
        with patch.object(open_app_feature, "load_app_list", return_value=[app]):
            with patch.object(open_app_feature, "get_allowed_app_targets", side_effect=lambda default=None: []):
                result = open_app_feature.open_app("spotify")

        self.assertIn("blocked by your security settings", result)

    def test_open_web_link_blocks_when_browser_links_disallowed(self):
        with patch.object(open_app_feature, "get_allowed_app_targets", side_effect=lambda default=None: []):
            result = open_app_feature.open_app("github.com")

        self.assertIn("Opening web links is blocked", result)


if __name__ == "__main__":
    unittest.main()
