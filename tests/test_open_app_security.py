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


if __name__ == "__main__":
    unittest.main()
