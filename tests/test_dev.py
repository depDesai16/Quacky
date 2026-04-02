import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import dev


class DevScriptTests(unittest.TestCase):
    def test_load_env_values_reads_key_value_pairs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("GEMINI_API_KEY=test-key\n# comment\nPORT=8000\n", encoding="utf-8")

            with patch.object(dev, "ENV_FILE", env_path):
                values = dev._load_env_values()

        self.assertEqual(values["GEMINI_API_KEY"], "test-key")
        self.assertEqual(values["PORT"], "8000")

    def test_has_api_key_checks_environment_and_env_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("GEMINI_API_KEY=file-key\n", encoding="utf-8")

            with patch.object(dev, "ENV_FILE", env_path):
                with patch.dict("os.environ", {}, clear=True):
                    self.assertTrue(dev._has_api_key())

                with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-key"}, clear=True):
                    self.assertTrue(dev._has_api_key())

    def test_doctor_reports_missing_setup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_dir = Path(tmpdir) / ".venv"
            env_path = Path(tmpdir) / ".env"

            with patch.object(dev, "VENV_DIR", venv_dir):
                with patch.object(dev, "ENV_FILE", env_path):
                    with patch.dict("os.environ", {}, clear=True):
                        result = dev.cmd_doctor(None)

        self.assertEqual(result, 1)

    def test_prelaunch_checks_stops_when_lint_fails(self):
        with patch.object(dev, "_has_api_key", return_value=True):
            with patch.object(dev, "_run_lint", return_value=1) as run_lint:
                with patch.object(dev, "_run_tests", return_value=0) as run_tests:
                    result = dev._prelaunch_checks(Path("/tmp/python"), skip_tests=False)

        run_lint.assert_called_once_with(Path("/tmp/python"))
        run_tests.assert_not_called()
        self.assertEqual(result, 1)

    def test_prelaunch_checks_runs_lint_and_tests_when_not_skipped(self):
        with patch.object(dev, "_has_api_key", return_value=True):
            with patch.object(dev, "_run_lint", return_value=0) as run_lint:
                with patch.object(dev, "_run_tests", return_value=0) as run_tests:
                    result = dev._prelaunch_checks(Path("/tmp/python"), skip_tests=False)

        run_lint.assert_called_once_with(Path("/tmp/python"))
        run_tests.assert_called_once_with(Path("/tmp/python"))
        self.assertEqual(result, 0)

    def test_prelaunch_checks_skips_lint_and_tests_when_requested(self):
        with patch.object(dev, "_has_api_key", return_value=True):
            with patch.object(dev, "_run_lint", return_value=0) as run_lint:
                with patch.object(dev, "_run_tests", return_value=0) as run_tests:
                    result = dev._prelaunch_checks(Path("/tmp/python"), skip_tests=True)

        run_lint.assert_not_called()
        run_tests.assert_not_called()
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
