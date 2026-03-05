from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLineEdit

from .ui import SettingsPanelMixin
from theme import ThemeManager
from .controller import SettingsController


class _ToastProxy:
    def __init__(self, callback):
        """Initialize the instance state."""
        self._callback = callback

    def show_message(self, message: str, kind: str = "success"):
        """Show message."""
        if self._callback is not None:
            self._callback(message, kind)


class SettingsPanel(SettingsPanelMixin, QWidget):
    model_visibility_changed = pyqtSignal(bool)
    speechtospeech_enabled_changed = pyqtSignal(bool)

    def __init__(
        self,
        model_window,
        speechtospeech_enabled: bool,
        toast_callback,
        client,
        parent=None,
    ):
        """Initialize the instance state."""
        super().__init__(parent)

        self.model_window = model_window
        self.speechtospeech_enabled = bool(speechtospeech_enabled)
        self.toast = _ToastProxy(toast_callback)
        self._settings_controller = SettingsController(client, parent=self)

        self._settings_tab_btns: list = []
        self._settings_row_labels: list = []
        self._settings_dividers: list = []
        self._settings_inputs: list = []
        self._settings_selects: list = []
        self._settings_input_hints: list = []
        self._settings_cards: list = []
        self._settings_rows: list = []
        self._settings_action_buttons: list = []
        self._api_test_worker = None
        self._api_key_input = None
        self._api_key_reveal_btn = None
        self._api_key_save_btn = None
        self._api_key_test_btn = None
        self._api_key_remove_btn = None
        self._saved_api_key = ""

        self._settings_container = self._build_settings_page()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._settings_container, 1)

        self._settings_controller.saved_api_key_loaded.connect(
            self._on_saved_api_key_loaded
        )
        self._settings_controller.api_key_test_result.connect(
            self._on_api_key_test_result
        )
        self._settings_controller.api_key_test_finished.connect(
            self._on_api_key_test_finished
        )

        self.apply_theme(ThemeManager.tokens())
        ThemeManager.subscribe(self.apply_theme)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        if hasattr(self, "_theme_mode_combo"):
            idx = self._theme_mode_combo.findData(ThemeManager.preference())
            if idx >= 0:
                from PyQt6.QtCore import QSignalBlocker

                with QSignalBlocker(self._theme_mode_combo):
                    self._theme_mode_combo.setCurrentIndex(idx)
        if hasattr(self, "_settings_container"):
            self._update_settings_theme(tokens)

    def prepare_for_show(self):
        """Handle prepare for show."""
        if hasattr(self, "_theme_mode_combo"):
            idx = self._theme_mode_combo.findData(ThemeManager.preference())
            if idx >= 0:
                from PyQt6.QtCore import QSignalBlocker

                with QSignalBlocker(self._theme_mode_combo):
                    self._theme_mode_combo.setCurrentIndex(idx)
        if hasattr(self, "_api_key_input") and self._api_key_input is not None:
            current = self._api_key_input.text()
            if not current.strip() and self._saved_api_key:
                self._api_key_input.setText(self._saved_api_key)
        self._update_api_key_action_state()
        self._settings_controller.refresh_saved_api_key_async()

    def _on_saved_api_key_loaded(self, saved_key: str, _error: str):
        """Handle saved api key loaded callbacks."""
        previous = self._saved_api_key
        self._saved_api_key = saved_key
        if self._api_key_input is None:
            return
        current = self._api_key_input.text().strip()
        if (not current) or (current == previous):
            self._api_key_input.setText(saved_key)
        self._update_api_key_action_state()

    def _update_api_key_action_state(self, *_args):
        """Update api key action state."""
        key_text = self._api_key_input.text().strip() if self._api_key_input else ""
        saved = bool(getattr(self, "_saved_api_key", ""))

        if self._api_key_save_btn is not None:
            self._api_key_save_btn.setEnabled(bool(key_text))
        if self._api_key_test_btn is not None:
            self._api_key_test_btn.setEnabled(
                bool(key_text) and not self._settings_controller.is_api_key_test_running()
            )
        if self._api_key_remove_btn is not None:
            self._api_key_remove_btn.setEnabled(bool(key_text) or saved)

    def _on_save_api_key_clicked(self):
        """Handle save api key clicked callbacks."""
        if self._api_key_input is None:
            return
        key = self._api_key_input.text().strip()
        if not key:
            self.toast.show_message("Enter an API key to save.", kind="warn")
            return
        ok, message = self._settings_controller.save_api_key(key)
        if not ok:
            self.toast.show_message(message, kind="error")
            return
        self._saved_api_key = key
        self._update_api_key_action_state()
        self.toast.show_message(message, kind="success")

    def _on_remove_api_key_clicked(self):
        """Handle remove api key clicked callbacks."""
        if self._api_key_input is not None:
            self._api_key_input.clear()
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self._api_key_reveal_btn is not None:
            from PyQt6.QtCore import QSignalBlocker

            blocker = QSignalBlocker(self._api_key_reveal_btn)
            self._api_key_reveal_btn.setChecked(False)
            self._api_key_reveal_btn.setText("Reveal")
            del blocker

        ok, message = self._settings_controller.remove_api_key()
        if not ok:
            self.toast.show_message(message, kind="error")
            return
        self._saved_api_key = ""
        self._update_api_key_action_state()
        self.toast.show_message(message, kind="warn")

    def _on_test_api_key_clicked(self):
        """Handle test api key clicked callbacks."""
        if self._api_key_input is None:
            return

        key = self._api_key_input.text().strip()
        if not key:
            self.toast.show_message("Enter an API key first.", kind="warn")
            return

        started = self._settings_controller.test_api_key_async(key)
        if not started:
            return
        if self._api_key_test_btn is not None:
            self._api_key_test_btn.setEnabled(False)
            self._api_key_test_btn.setText("Testing...")

    def _on_api_key_test_result(self, ok: bool, message: str):
        """Handle api key test result callbacks."""
        self.toast.show_message(message, kind="success" if ok else "error")

    def _on_api_key_test_finished(self):
        """Handle api key test finished callbacks."""
        if self._api_key_test_btn is not None:
            self._api_key_test_btn.setText("Test Connection")
        self._update_api_key_action_state()

    def set_model_visible(self, visible: bool):
        """Set model visible."""
        if self.model_window is not None:
            self.model_window.show() if visible else self.model_window.hide()
        self.model_visibility_changed.emit(bool(visible))

    def set_speechtospeech_enabled(self, enabled: bool):
        """Set speechtospeech enabled."""
        self.speechtospeech_enabled = bool(enabled)
        self.speechtospeech_enabled_changed.emit(bool(enabled))

    def _show_settings(self):
        """Show settings."""
        return

    def _show_chat(self):
        """Show chat."""
        return

    def shutdown(self):
        """Handle shutdown."""
        self._settings_controller.shutdown()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass

