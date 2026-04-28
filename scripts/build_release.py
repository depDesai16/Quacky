#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from PyInstaller.__main__ import run as pyinstaller_run

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build" / "pyinstaller"
ASSET_SUFFIXES = {".css", ".json", ".png", ".txt"}


def _add_data_arg(path: Path) -> str:
    destination = path.relative_to(ROOT_DIR).parent.as_posix()
    return f"{path}{os.pathsep}{destination}"


def _build_frontend(extra_args: list[str]) -> None:
    pyinstaller_run(
        [
            "--noconfirm",
            "--clean",
            "--windowed",
            "--name",
            "Quacky",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR / "frontend"),
            "--specpath",
            str(BUILD_DIR / "frontend"),
            *extra_args,
            str(ROOT_DIR / "app.py"),
        ]
    )


def _build_backend(extra_args: list[str]) -> None:
    pyinstaller_run(
        [
            "--noconfirm",
            "--clean",
            "--onefile",
            "--console",
            "--name",
            "QuackyBackend",
            "--distpath",
            str(DIST_DIR / "Quacky"),
            "--workpath",
            str(BUILD_DIR / "backend"),
            "--specpath",
            str(BUILD_DIR / "backend"),
            *extra_args,
            str(ROOT_DIR / "backend" / "server.py"),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build release artifacts with PyInstaller")
    parser.add_argument("--clean", action="store_true", help="Remove prior build outputs before packaging")
    args = parser.parse_args()

    if args.clean:
        for path in (DIST_DIR, BUILD_DIR):
            if path.exists():
                import shutil

                shutil.rmtree(path)

    extra_args: list[str] = ["--paths", str(ROOT_DIR)]
    for base in (ROOT_DIR / "frontend", ROOT_DIR / "backend"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES:
                extra_args.extend(["--add-data", _add_data_arg(path)])

    _build_frontend(extra_args)
    _build_backend(extra_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
