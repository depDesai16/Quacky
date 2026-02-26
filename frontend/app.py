import sys
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon, QMenu
from settings_window import SettingsWindow
from quacky_gui import QuackyGUI
from draw_icon import draw_icon

def show_main():
    main_win.show()
    main_win.raise_()
    main_win.activateWindow()

def show_settings():
    settings_win.show()
    settings_win.raise_()
    settings_win.activateWindow()

def on_tray_activated(reason):
    # Left-click on tray to open main window
    if reason == QSystemTrayIcon.ActivationReason.Trigger:
        if main_win.isVisible():
            main_win.hide()
        else:
            show_main()

def build_system_tray():
    tray = QSystemTrayIcon(draw_icon(), parent = app)
    tray.setToolTip("Quacky")

    #### Right-Click Menu

    tray_menu = QMenu()
    with open("css/tray_menu.css", "r") as f:
        tray_menu.setStyleSheet(f.read())

    action_open = tray_menu.addAction(" ⟳  Open Quacky")
    action_settings = tray_menu.addAction("⚙  Settings")
    tray_menu.addSeparator()
    action_quit = tray_menu.addAction(" ×   Quit")

    action_open.triggered.connect(show_main)
    action_settings.triggered.connect(show_settings)
    action_quit.triggered.connect(app.quit)

    tray.activated.connect(on_tray_activated)
    tray.setContextMenu(tray_menu)
    return tray


#### Main

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep alive when windows hidden

    main_win = QuackyGUI()
    settings_win = SettingsWindow(model_visible = False, speechtospeech_enabled = False)
    settings_win.model_visibility_changed.connect(main_win.set_model_visible) # Wire settings to model visibility
    settings_win.speechtospeech_enabled_changed.connect(main_win.set_speechtospeech_enabled) # Wire settings to speech-to-speech

    tray = build_system_tray()
    tray.show()

    sys.exit(app.exec())