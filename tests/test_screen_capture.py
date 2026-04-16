import importlib
import os
import sys
import unittest
from unittest.mock import patch


_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "chat",
    "screen_capture.py",
)
_SPEC = importlib.util.spec_from_file_location("quacky_screen_capture", _MODULE_PATH)
screen_capture = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
sys.modules[_SPEC.name] = screen_capture
_SPEC.loader.exec_module(screen_capture)


class ScreenCaptureStrategyTests(unittest.TestCase):
    def test_wayland_prefers_qt_screen_capture(self):
        with patch.object(screen_capture.sys, "platform", "linux"):
            with patch.dict(screen_capture.os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=False):
                self.assertEqual(
                    screen_capture._preferred_capture_methods(),
                    ("qt_screen_capture", "qt_grab"),
                )

    def test_windows_includes_powershell_fallback(self):
        with patch.object(screen_capture.sys, "platform", "win32"):
            with patch.dict(screen_capture.os.environ, {}, clear=True):
                self.assertEqual(
                    screen_capture._preferred_capture_methods(),
                    ("qt_grab", "powershell"),
                )

    def test_macos_includes_screencapture_fallback(self):
        with patch.object(screen_capture.sys, "platform", "darwin"):
            with patch.dict(screen_capture.os.environ, {}, clear=True):
                self.assertEqual(
                    screen_capture._preferred_capture_methods(),
                    ("qt_grab", "screencapture"),
                )


if __name__ == "__main__":
    unittest.main()
