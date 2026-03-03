"""
app.py — Application entrypoint.

Changes from original:
  Line 1 (import): QuackyGUI → QuackyWindow
  Everything else is bit-for-bit identical to the original app.py.
"""

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(FRONTEND_DIR)
sys.path.insert(0, ROOT_DIR)


def _configure_platform_env() -> None:
    if sys.platform.startswith("linux"):
        session_type = (os.getenv("XDG_SESSION_TYPE") or "").lower()
        has_wayland = bool(os.getenv("WAYLAND_DISPLAY")) or session_type == "wayland"

        if has_wayland:
            os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")
            os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
            # Wayland compositors vary; software fallback avoids hard failures.
            os.environ.setdefault("QT_OPENGL", "software")
        else:
            os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
            os.environ.setdefault("PYOPENGL_PLATFORM", "x11")

        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    elif sys.platform == "darwin":
        # Improve consistency for macOS compositing and high-DPI displays.
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


_configure_platform_env()

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from settings_window import SettingsWindow
from quacky_window   import QuackyWindow                               
from draw_icon       import draw_icon
from backend.client  import QuackyClient



def _start_server() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "backend.server"],
        cwd=ROOT_DIR,
    )

def _wait_for_server(base_url: str, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False

def _load_system_prompt() -> str | None:
    path = os.path.join(ROOT_DIR, "backend", "system_prompt.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None



def show_main():
    main_win.show()
    main_win.raise_()
    main_win.activateWindow()

def show_settings():
    settings_win.show()
    settings_win.raise_()
    settings_win.activateWindow()

def on_tray_activated(reason):
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        if main_win.isVisible():
            main_win.hide()
        else:
            show_main()

def build_system_tray(app: QApplication) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(draw_icon(), parent=app)
    tray.setToolTip("Quacky")

    tray_menu = QMenu()
    css_path  = os.path.join(FRONTEND_DIR, "css", "tray_menu.css")
    with open(css_path, "r") as f:
        tray_menu.setStyleSheet(f.read())

    action_open     = tray_menu.addAction(" ⟳  Open Quacky")
    action_settings = tray_menu.addAction("⚙  Settings")
    tray_menu.addSeparator()
    action_quit     = tray_menu.addAction(" ×   Quit")

    action_open.triggered.connect(show_main)
    action_settings.triggered.connect(show_settings)
    action_quit.triggered.connect(app.quit)
    tray.activated.connect(on_tray_activated)
    tray.setContextMenu(tray_menu)
    return tray



if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    base_url = os.getenv("QUACKY_BASE_URL", "http://localhost:8000")

    server_proc = _start_server()

    if not _wait_for_server(base_url):
        QMessageBox.critical(None, "Quacky", "Backend server failed to start.")
        server_proc.terminate()
        sys.exit(1)

    client    = QuackyClient(base_url)
    system    = _load_system_prompt()
    chat_data = client.start_chat(system=system)
    chat_id   = chat_data.get("chat_id", "")

    if not chat_id:
        QMessageBox.critical(None, "Quacky", "Could not start chat session.")
        server_proc.terminate()
        sys.exit(1)

    main_win     = QuackyWindow(client=client, chat_id=chat_id)
    settings_win = SettingsWindow(model_visible=False, speechtospeech_enabled=False)

    settings_win.model_visibility_changed.connect(main_win.set_model_visible)
    settings_win.speechtospeech_enabled_changed.connect(main_win.set_speechtospeech_enabled)

    tray = build_system_tray(app)
    tray.show()
    main_win.show()

    def _on_quit():
        main_win.shutdown()
        if server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    app.aboutToQuit.connect(_on_quit)

    sys.exit(app.exec())
