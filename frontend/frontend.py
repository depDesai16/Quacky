import logging
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from widgets.quacky_widget import get_quacky_icon

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(FRONTEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _configure_platform_env() -> None:
    """Handle configure platform env."""
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

    if sys.platform.startswith("linux"):
        session_type = (os.getenv("XDG_SESSION_TYPE") or "").lower()
        has_wayland = bool(os.getenv("WAYLAND_DISPLAY")) or session_type == "wayland"

        if has_wayland:
            os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")
            os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
            os.environ.setdefault("QT_OPENGL", "software")
        else:
            os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
            os.environ.setdefault("PYOPENGL_PLATFORM", "x11")

        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    elif sys.platform == "darwin":
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")


_configure_platform_env()

from chat.window import QuackyWindow
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon
from theme import FONT_FAMILY_UI

from backend.client import QuackyClient
from backend.core.runtime_logging import configure_runtime_logging, install_exception_logging

LOGGER = logging.getLogger(__name__)
LOG_PATH = configure_runtime_logging("frontend")
install_exception_logging(LOGGER)


def _configure_app_identity(app: QApplication) -> None:
    """Handle configure app identity."""
    app.setApplicationName("Quacky")
    app.setApplicationDisplayName("Quacky")
    app.setOrganizationName("Quacky")
    app.setOrganizationDomain("quacky.local")
    app.setDesktopFileName("quacky")


def _start_server() -> subprocess.Popen:
    """Handle start server."""
    LOGGER.info("Starting backend subprocess from desktop app")
    return subprocess.Popen([sys.executable, "-m", "backend.server"], cwd=ROOT_DIR)


def _wait_for_server(base_url: str, timeout: float = 10.0) -> bool:
    """Handle wait for server."""
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
    """Load system prompt."""
    path = os.path.join(ROOT_DIR, "backend", "system_prompt.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def show_main():
    """Show main."""
    main_win.show()
    main_win.raise_()
    main_win.activateWindow()


def show_settings():
    """Show settings."""
    show_main()
    main_win._show_settings()


def on_tray_activated(reason):
    """Handle tray activated callbacks."""
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        if main_win.isVisible():
            main_win.hide()
        else:
            show_main()


def build_system_tray(app: QApplication) -> QSystemTrayIcon:
    """Build system tray."""
    tray = QSystemTrayIcon(get_quacky_icon(), parent=app)
    tray.setToolTip("Quacky")

    tray_menu = QMenu()
    css_path = os.path.join(FRONTEND_DIR, "css", "tray_menu.css")
    with open(css_path, "r", encoding="utf-8") as f:
        tray_menu.setStyleSheet(f.read())

    action_open     = tray_menu.addAction("Open Quacky")
    action_settings = tray_menu.addAction("Settings")
    tray_menu.addSeparator()
    action_quit = tray_menu.addAction("Quit")

    action_open.triggered.connect(show_main)
    action_settings.triggered.connect(show_settings)
    action_quit.triggered.connect(app.quit)
    tray.activated.connect(on_tray_activated)
    tray.setContextMenu(tray_menu)
    return tray


def run_it():
    """Entry point called from root app.py"""
    LOGGER.info("Launching Quacky desktop app")
    LOGGER.info("Runtime log file: %s", LOG_PATH)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    _configure_app_identity(app)

    app.setStyle("Fusion")

    app_font = QFont(FONT_FAMILY_UI, 10)
    app_font.setStyleStrategy(
        QFont.StyleStrategy.PreferAntialias
        | QFont.StyleStrategy.PreferQuality
    )
    if FONT_FAMILY_UI not in set(QFontDatabase.families()):
        app_font = QFont()
        app_font.setPointSize(10)
    app.setFont(app_font)

    _shutdown_requested = False
    base_url = os.getenv("QUACKY_BASE_URL", "http://localhost:8000")
    server_proc = _start_server()

    if not _wait_for_server(base_url):
        LOGGER.error("Backend server failed health check at %s", base_url)
        QMessageBox.critical(None, "Quacky", "Backend server failed to start.")
        server_proc.terminate()
        sys.exit(1)

    client   = QuackyClient(base_url)
    system   = _load_system_prompt()
    chat_data = client.start_chat(system=system)
    chat_id  = chat_data.get("chat_id", "")

    if not chat_id:
        LOGGER.error("Could not start initial chat session")
        QMessageBox.critical(None, "Quacky", "Could not start chat session.")
        server_proc.terminate()
        sys.exit(1)

    global main_win
    main_win = QuackyWindow(client=client, chat_id=chat_id)

    tray = build_system_tray(app)
    tray.show()
    main_win.show()

    def _on_quit():
        nonlocal _shutdown_requested
        if _shutdown_requested:
            return
        _shutdown_requested = True
        LOGGER.info("Shutting down Quacky desktop app")
        main_win.shutdown()
        if server_proc.poll() is None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                LOGGER.warning("Backend subprocess did not exit cleanly; killing it")
                server_proc.kill()

    def _handle_exit_signal(_sig, _frame):
        LOGGER.info("Received exit signal; quitting desktop app")
        app.quit()

    sig_timer = QTimer()
    sig_timer.setInterval(250)
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start()

    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _handle_exit_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_exit_signal)

    app.aboutToQuit.connect(_on_quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    run_it()
