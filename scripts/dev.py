#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT_DIR / ".venv"
ENV_EXAMPLE = ROOT_DIR / ".env.example"
ENV_FILE = ROOT_DIR / ".env"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _run(cmd: list[str], cwd: Path | None = None) -> int:
    return subprocess.call(cmd, cwd=str(cwd or ROOT_DIR))


def _require_venv() -> Path:
    python_path = _venv_python()
    if not python_path.exists():
        raise SystemExit("Missing .venv. Run setup first.")
    return python_path


def _run_tests(venv_python: Path) -> int:
    return _run([str(venv_python), "-m", "pytest", "-q"], cwd=ROOT_DIR)


def _prelaunch_checks(venv_python: Path, skip_tests: bool) -> int:
    if not _has_api_key():
        raise SystemExit("Missing GEMINI_API_KEY or GOOGLE_API_KEY in .env or environment.")
    if skip_tests:
        return 0

    print("Running test suite before launch...")
    result = _run_tests(venv_python)
    if result != 0:
        print("Test suite failed. Fix the failing tests or rerun with --skip-tests.")
    return result


def _create_venv(python_cmd: str) -> None:
    if not VENV_DIR.exists():
        result = _run([python_cmd, "-m", "venv", str(VENV_DIR)])
        if result != 0:
            raise SystemExit(result)


def _copy_env_template() -> None:
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
        print("Created .env from .env.example.")


def _load_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values

    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _has_api_key() -> bool:
    env_values = _load_env_values()
    return bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or env_values.get("GEMINI_API_KEY")
        or env_values.get("GOOGLE_API_KEY")
    )


def _print_next_steps() -> None:
    print("Setup complete.")
    if not _has_api_key():
        print("Next: add GEMINI_API_KEY or GOOGLE_API_KEY to .env before starting Quacky.")
    print("Run the test suite: python scripts/dev.py test")
    print("Run the desktop app: python scripts/dev.py ui")
    print("Run the backend: python scripts/dev.py server")
    print("Check local setup: python scripts/dev.py doctor")


def cmd_setup(args: argparse.Namespace) -> int:
    python_cmd = args.python or ("python" if os.name == "nt" else "python3")
    _create_venv(python_cmd)
    venv_python = _venv_python()

    install_steps = [
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        [str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
    ]

    for cmd in install_steps:
        result = _run(cmd)
        if result != 0:
            return result

    _copy_env_template()
    _print_next_steps()
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    issues: list[str] = []

    if not VENV_DIR.exists():
        issues.append("Missing .venv")
    if not ENV_FILE.exists():
        issues.append("Missing .env")
    if not _has_api_key():
        issues.append("Missing GEMINI_API_KEY or GOOGLE_API_KEY")

    if issues:
        print("Setup check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Setup check passed.")
    return 0


def cmd_test(_args: argparse.Namespace) -> int:
    venv_python = _require_venv()
    return _run_tests(venv_python)


def cmd_server(args: argparse.Namespace) -> int:
    venv_python = _require_venv()
    prelaunch_result = _prelaunch_checks(venv_python, args.skip_tests)
    if prelaunch_result != 0:
        return prelaunch_result
    return _run([str(venv_python), "-m", "backend.server"])


def cmd_ui(args: argparse.Namespace) -> int:
    venv_python = _require_venv()
    prelaunch_result = _prelaunch_checks(venv_python, args.skip_tests)
    if prelaunch_result != 0:
        return prelaunch_result
    return _run([str(venv_python), "frontend/app.py"])


def cmd_cli(args: argparse.Namespace) -> int:
    venv_python = _require_venv()
    prelaunch_result = _prelaunch_checks(venv_python, args.skip_tests)
    if prelaunch_result != 0:
        return prelaunch_result
    return _run([str(venv_python), "-m", "backend.interact.text_to_text.cli"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quacky developer helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Create venv, install deps, and seed .env")
    setup_parser.add_argument("--python", help="Python executable to use for venv creation")
    setup_parser.set_defaults(func=cmd_setup)

    doctor_parser = subparsers.add_parser("doctor", help="Validate local Quacky setup")
    doctor_parser.set_defaults(func=cmd_doctor)

    test_parser = subparsers.add_parser("test", help="Run the full pytest suite")
    test_parser.set_defaults(func=cmd_test)

    server_parser = subparsers.add_parser("server", help="Run the backend server")
    server_parser.add_argument("--skip-tests", action="store_true", help="Skip running the test suite before launch")
    server_parser.set_defaults(func=cmd_server)

    ui_parser = subparsers.add_parser("ui", help="Run the desktop app")
    ui_parser.add_argument("--skip-tests", action="store_true", help="Skip running the test suite before launch")
    ui_parser.set_defaults(func=cmd_ui)

    cli_parser = subparsers.add_parser("cli", help="Run the text client against a running backend")
    cli_parser.add_argument("--skip-tests", action="store_true", help="Skip running the test suite before launch")
    cli_parser.set_defaults(func=cmd_cli)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
