import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core import runtime_logging


class RuntimeLoggingTests(unittest.TestCase):
    def test_get_log_path_creates_logs_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir) / "logs"

            with patch.object(runtime_logging, "LOGS_DIR", logs_dir):
                log_path = runtime_logging.get_log_path("backend")

            self.assertEqual(log_path, logs_dir / "backend.log")
            self.assertTrue(logs_dir.exists())

    def test_configure_runtime_logging_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = Path(tmpdir) / "logs"
            root_logger = logging.getLogger("quacky-test-root")
            root_logger.handlers.clear()
            marker = "_quacky_logging_backend"
            if hasattr(root_logger, marker):
                delattr(root_logger, marker)

            with patch.object(runtime_logging, "LOGS_DIR", logs_dir):
                with patch("logging.getLogger", return_value=root_logger):
                    runtime_logging.configure_runtime_logging("backend")
                    runtime_logging.configure_runtime_logging("backend")

            self.assertEqual(len(root_logger.handlers), 1)
            self.assertTrue(hasattr(root_logger, marker))


if __name__ == "__main__":
    unittest.main()
