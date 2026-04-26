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

    def test_not_found_app_offers_close_match_suggestion(self):
        app = open_app_feature.AppEntry(
            name="Spotify",
            command="spotify",
            os_commands={},
            aliases=("music",),
        )
        with patch.object(open_app_feature, "load_app_list", return_value=[app]):
            result = open_app_feature.open_app("spotfy")

        self.assertIn("couldn't find 'spotfy'", result.lower())
        self.assertIn("Spotify", result)

    def test_ambiguous_app_requests_exact_name(self):
        firefox = open_app_feature.AppEntry(
            name="Mozilla Firefox",
            command="firefox",
            os_commands={},
            aliases=("firefox",),
        )
        chrome = open_app_feature.AppEntry(
            name="Google Chrome",
            command="chrome",
            os_commands={},
            aliases=("browser",),
        )
        with patch.object(open_app_feature, "load_app_list", return_value=[firefox, chrome]):
            result = open_app_feature.open_app("o")

        self.assertIn("multiple matches", result)
        self.assertIn("Say the exact app name", result)

    def test_missing_desktop_app_opens_web_fallback(self):
        app = open_app_feature.AppEntry(
            name="Spotify",
            command="spotify",
            os_commands={},
            aliases=(),
        )
        with patch.object(open_app_feature, "load_app_list", return_value=[app]):
            with patch.object(
                open_app_feature,
                "get_allowed_app_targets",
                side_effect=lambda default=None: ["Spotify"],
            ):
                with patch.object(open_app_feature, "_ensure_command_exists", return_value=False):
                    with patch.object(
                        open_app_feature.webbrowser,
                        "open",
                        return_value=True,
                    ) as open_mock:
                        result = open_app_feature.open_app("spotify")

        open_mock.assert_called_once_with("https://open.spotify.com/", new=2)
        self.assertIn("Desktop app unavailable", result)
        self.assertIn("Opened web fallback", result)


if __name__ == "__main__":
    unittest.main()
