#!/usr/bin/env python3
"""
app.py  –  Quacky Desktop  (entry point)
─────────────────────────────────────────
Drop this file in your Quacky project root (same level as backend/).
The frontend/ folder must sit beside it.

Run:
    python app.py
    # or from any subdirectory:
    python path/to/app.py
"""

import sys
import os

# Make sure the project root (where app.py lives) is importable
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from PySide6.QtWidgets import QApplication
from quacky.theme       import apply_theme
from quacky.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()