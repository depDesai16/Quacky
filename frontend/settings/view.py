import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget
from theme import ThemeManager

from .controller import SettingsController
from .ui import SettingsPanelMixin

LOGGER = logging.getLogger(__name__)


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
    open_app_confirmation_enabled_changed = pyqtSignal(bool)
    timer_confirmation_enabled_changed = pyqtSignal(bool)
    screen_viewing_enabled_changed = pyqtSignal(bool)

    def __init__(
        self,
        model_window,
        speechtospeech_enabled: bool,
        open_app_confirmation_enabled: bool,
        timer_confirmation_enabled: bool,
        screen_viewing_enabled: bool,
        toast_callback,
        client,
        parent=None,
    ):
        """Initialize the instance state."""
        super().__init__(parent)

        self.model_window = model_window
        self._client = client
        self.speechtospeech_enabled = bool(speechtospeech_enabled)
        self.open_app_confirmation_enabled = bool(open_app_confirmation_enabled)
        self.timer_confirmation_enabled = bool(timer_confirmation_enabled)
        self.screen_viewing_enabled = bool(screen_viewing_enabled)
        self.app_control_suggestions_enabled = False
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
        self._has_saved_api_key = False
        self._app_control_toggles: dict[str, object] = {}
        self._setup_status_label = None
        self._app_controls_layout = None
        self._preferences_layout = None
        self._tasks_layout = None
        self._toggle_app_control_suggestions = None

        self._settings_container = self._build_settings_page()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._settings_container, 1)

        self._settings_controller.saved_api_key_loaded.connect(
            self._on_saved_api_key_loaded
        )
        self._settings_controller.confirmation_settings_loaded.connect(
            self._on_confirmation_settings_loaded
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
        self._update_api_key_action_state()
        self._settings_controller.refresh_confirmation_settings_async()
        self._settings_controller.refresh_saved_api_key_async()
        self._refresh_security_state()

    def _on_confirmation_settings_loaded(self, open_enabled, timer_enabled, screen_enabled, _error: str):
        """Handle async confirmation settings refresh callbacks."""
        if open_enabled is not None:
            self.open_app_confirmation_enabled = bool(open_enabled)
            if (
                hasattr(self, "_toggle_open_app_confirm")
                and self._toggle_open_app_confirm is not None
                and self._toggle_open_app_confirm.isChecked()
                != self.open_app_confirmation_enabled
            ):
                from PyQt6.QtCore import QSignalBlocker

                blocker = QSignalBlocker(self._toggle_open_app_confirm)
                self._toggle_open_app_confirm.setChecked(
                    self.open_app_confirmation_enabled
                )
                del blocker

        if timer_enabled is not None:
            self.timer_confirmation_enabled = bool(timer_enabled)
            if (
                hasattr(self, "_toggle_timer_confirm")
                and self._toggle_timer_confirm is not None
                and self._toggle_timer_confirm.isChecked()
                != self.timer_confirmation_enabled
            ):
                from PyQt6.QtCore import QSignalBlocker

                blocker = QSignalBlocker(self._toggle_timer_confirm)
                self._toggle_timer_confirm.setChecked(
                    self.timer_confirmation_enabled
                )
                del blocker

        if screen_enabled is not None:
            self.screen_viewing_enabled = bool(screen_enabled)
            if (
                hasattr(self, "_toggle_screen_viewing")
                and self._toggle_screen_viewing is not None
                and self._toggle_screen_viewing.isChecked()
                != self.screen_viewing_enabled
            ):
                from PyQt6.QtCore import QSignalBlocker

                blocker = QSignalBlocker(self._toggle_screen_viewing)
                self._toggle_screen_viewing.setChecked(
                    self.screen_viewing_enabled
                )
                del blocker

    def _refresh_open_app_confirmation_setting(self):
        """Refresh open-app confirmation state from backend for UI sync."""
        if self._client is None or not hasattr(
            self._client, "get_open_app_confirmation_settings"
        ):
            return
        try:
            result = self._client.get_open_app_confirmation_settings()
        except Exception:
            return
        if isinstance(result, dict) and "enabled" in result:
            self.open_app_confirmation_enabled = bool(result.get("enabled"))
            if (
                hasattr(self, "_toggle_open_app_confirm")
                and self._toggle_open_app_confirm is not None
                and self._toggle_open_app_confirm.isChecked()
                != self.open_app_confirmation_enabled
            ):
                from PyQt6.QtCore import QSignalBlocker

                blocker = QSignalBlocker(self._toggle_open_app_confirm)
                self._toggle_open_app_confirm.setChecked(
                    self.open_app_confirmation_enabled
                )
                del blocker

    def _refresh_timer_confirmation_setting(self):
        """Refresh timer confirmation state from backend for UI sync."""
        if self._client is None or not hasattr(
            self._client, "get_timer_confirmation_settings"
        ):
            return
        try:
            result = self._client.get_timer_confirmation_settings()
        except Exception:
            return
        if isinstance(result, dict) and "enabled" in result:
            self.timer_confirmation_enabled = bool(result.get("enabled"))
            if (
                hasattr(self, "_toggle_timer_confirm")
                and self._toggle_timer_confirm is not None
                and self._toggle_timer_confirm.isChecked()
                != self.timer_confirmation_enabled
            ):
                from PyQt6.QtCore import QSignalBlocker

                blocker = QSignalBlocker(self._toggle_timer_confirm)
                self._toggle_timer_confirm.setChecked(
                    self.timer_confirmation_enabled
                )
                del blocker

    def _on_saved_api_key_loaded(self, has_saved_key: bool, _error: str):
        """Handle saved api key loaded callbacks."""
        self._has_saved_api_key = bool(has_saved_key)
        self._update_api_key_action_state()

    def _update_api_key_action_state(self, *_args):
        """Update api key action state."""
        key_text = self._api_key_input.text().strip() if self._api_key_input else ""
        saved = bool(getattr(self, "_has_saved_api_key", False))

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
        self._has_saved_api_key = True
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
        self._has_saved_api_key = False
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

    def _clear_layout(self, layout):
        """Delete all child widgets/layout items from a layout."""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)
            if widget is not None:
                widget.deleteLater()

    def _refresh_security_state(self):
        """Refresh setup, app-control, and memory data."""
        self._refresh_setup_status()
        self._refresh_app_controls()
        self._refresh_memory_snapshot()

    def _refresh_setup_status(self):
        """Load setup status and render a concise checklist."""
        if self._client is None or not hasattr(self._client, "get_setup_status"):
            return
        try:
            result = self._client.get_setup_status()
        except Exception as exc:
            if self._setup_status_label is not None:
                self._setup_status_label.setText(f"Could not load setup status: {exc}")
            return
        if not isinstance(result, dict) or self._setup_status_label is None:
            return

        items = result.get("items") if isinstance(result.get("items"), dict) else {}
        lines = []
        for key in ("api_key", "microphone", "calendar", "screen_viewing"):
            item = items.get(key) if isinstance(items, dict) else None
            if not isinstance(item, dict):
                continue
            marker = "Ready" if bool(item.get("ready")) else "Needs attention"
            title = str(item.get("title", key)).strip()
            detail = str(item.get("detail", "")).strip()
            lines.append(f"<b>{title}</b>: {marker}<br>{detail}")
        self._setup_status_label.setText("<br><br>".join(lines))

    def _refresh_app_controls(self):
        """Load app-control toggles from backend state."""
        if self._client is None or not hasattr(self._client, "get_app_control_settings"):
            return
        try:
            result = self._client.get_app_control_settings()
        except Exception as exc:
            if self._app_controls_layout is not None:
                self._clear_layout(self._app_controls_layout)
                error = QLineEdit()
                error.setObjectName("settingsInput")
                error.setReadOnly(True)
                error.setText(f"Could not load app controls: {exc}")
                self._app_controls_layout.addWidget(error)
            return
        if not isinstance(result, dict) or self._app_controls_layout is None:
            return

        suggest_enabled = bool(result.get("suggest_updates_enabled", False))
        self.app_control_suggestions_enabled = suggest_enabled
        if (
            self._toggle_app_control_suggestions is not None
            and self._toggle_app_control_suggestions.isChecked() != suggest_enabled
        ):
            from PyQt6.QtCore import QSignalBlocker

            blocker = QSignalBlocker(self._toggle_app_control_suggestions)
            self._toggle_app_control_suggestions.setChecked(suggest_enabled)
            del blocker

        self._clear_layout(self._app_controls_layout)
        self._app_control_toggles = {}
        options = result.get("options") if isinstance(result.get("options"), list) else []
        for item in options:
            if not isinstance(item, dict):
                continue
            target_id = str(item.get("target_id", "")).strip()
            label = str(item.get("label", target_id)).strip() or target_id
            kind = str(item.get("kind", "app")).strip().lower()
            subtitle = (
                "Allow Quacky to open links in your browser."
                if kind == "web"
                else "Allow Quacky to open this application."
            )
            row, toggle = self._make_settings_toggle_row(
                label,
                subtitle,
                bool(item.get("allowed")),
            )
            toggle.toggled.connect(
                lambda checked, target=target_id: self._on_app_control_toggled(target, checked)
            )
            self._app_controls_layout.addWidget(row)
            self._app_control_toggles[target_id] = toggle
        self._app_controls_layout.addStretch(1)

    def _on_app_control_toggled(self, _target_id: str, _checked: bool):
        """Persist app-control changes after any toggle update."""
        if self._client is None or not hasattr(self._client, "set_app_control_settings"):
            return
        allowed_targets = [
            target_id
            for target_id, toggle in self._app_control_toggles.items()
            if toggle.isChecked()
        ]
        try:
            result = self._client.set_app_control_settings(
                allowed_targets,
                suggest_updates_enabled=self.app_control_suggestions_enabled,
            )
        except Exception as exc:
            self.toast.show_message(f"Failed to update app controls: {exc}", kind="error")
            self._refresh_app_controls()
            return
        if isinstance(result, dict) and "error" in result:
            self.toast.show_message(f"Failed to update app controls: {result['error']}", kind="error")
            self._refresh_app_controls()
            return
        self.toast.show_message("Updated app control permissions.", kind="success")

    def set_app_control_suggestions_enabled(self, enabled: bool):
        """Persist whether Quacky may suggest allowlist updates."""
        requested = bool(enabled)
        self.app_control_suggestions_enabled = requested
        if self._client is None or not hasattr(self._client, "set_app_control_settings"):
            return

        allowed_targets = [
            target_id
            for target_id, toggle in self._app_control_toggles.items()
            if toggle.isChecked()
        ]
        try:
            result = self._client.set_app_control_settings(
                allowed_targets,
                suggest_updates_enabled=requested,
            )
        except Exception as exc:
            self.toast.show_message(
                f"Failed to update app-control suggestions: {exc}",
                kind="error",
            )
            self._refresh_app_controls()
            return
        if isinstance(result, dict) and "error" in result:
            self.toast.show_message(
                f"Failed to update app-control suggestions: {result['error']}",
                kind="error",
            )
            self._refresh_app_controls()
            return
        self.toast.show_message(
            "Updated app-control suggestion setting.",
            kind="success",
        )

    def _refresh_memory_snapshot(self):
        """Load remembered preferences and tasks into editable rows."""
        if self._client is None or not hasattr(self._client, "get_memory_snapshot"):
            return
        try:
            result = self._client.get_memory_snapshot()
        except Exception as exc:
            self.toast.show_message(f"Failed to load memory: {exc}", kind="error")
            return
        if not isinstance(result, dict):
            return
        self._render_memory_scope(
            self._preferences_layout,
            "preferences",
            result.get("preferences"),
            "No remembered preferences yet.",
        )
        self._render_memory_scope(
            self._tasks_layout,
            "tasks",
            result.get("tasks"),
            "No remembered task notes yet.",
        )

    def _render_memory_scope(self, layout, scope: str, items, empty_text: str):
        """Render editable memory rows for one scope."""
        if layout is None:
            return
        self._clear_layout(layout)
        rows = items if isinstance(items, list) else []
        if not rows:
            hint = QLineEdit()
            hint.setObjectName("settingsInput")
            hint.setReadOnly(True)
            hint.setText(empty_text)
            layout.addWidget(hint)
            return

        for item in rows:
            if not isinstance(item, dict):
                continue
            value = str(item.get("value", "")).strip()
            if not value:
                continue
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(8)

            editor = QLineEdit(value)
            editor.setObjectName("settingsInput")
            self._settings_inputs.append(editor)
            row_lay.addWidget(editor, 1)

            save_btn = QPushButton("Save")
            save_btn.setObjectName("settingsActionButton")
            save_btn.setProperty("role", "secondary")
            save_btn.setMinimumHeight(34)
            save_btn.clicked.connect(
                lambda _=False, s=scope, old=value, edit=editor: self._on_memory_save(s, old, edit.text())
            )
            row_lay.addWidget(save_btn, 0)

            remove_btn = QPushButton("Remove")
            remove_btn.setObjectName("settingsActionButton")
            remove_btn.setProperty("role", "danger")
            remove_btn.setMinimumHeight(34)
            remove_btn.clicked.connect(
                lambda _=False, s=scope, old=value: self._on_memory_remove(s, old)
            )
            row_lay.addWidget(remove_btn, 0)

            layout.addWidget(row)
        layout.addStretch(1)

    def _on_memory_save(self, scope: str, old_value: str, new_value: str):
        """Persist an edited remembered item."""
        if self._client is None or not hasattr(self._client, "update_memory_item"):
            return
        if not str(new_value or "").strip():
            self.toast.show_message("Memory items cannot be empty.", kind="warn")
            return
        try:
            result = self._client.update_memory_item(scope, old_value, new_value)
        except Exception as exc:
            self.toast.show_message(f"Failed to update memory: {exc}", kind="error")
            return
        if isinstance(result, dict) and "error" in result:
            self.toast.show_message(str(result["error"]), kind="error")
            return
        self.toast.show_message("Updated remembered item.", kind="success")
        self._refresh_memory_snapshot()

    def _on_memory_remove(self, scope: str, value: str):
        """Remove one remembered item."""
        if self._client is None or not hasattr(self._client, "forget_memory_item"):
            return
        try:
            result = self._client.forget_memory_item(scope, value)
        except Exception as exc:
            self.toast.show_message(f"Failed to remove memory item: {exc}", kind="error")
            return
        if isinstance(result, dict) and "error" in result:
            self.toast.show_message(str(result["error"]), kind="error")
            return
        message = str(result.get("message", "Removed remembered item.")) if isinstance(result, dict) else "Removed remembered item."
        self.toast.show_message(message, kind="warn")
        self._refresh_memory_snapshot()

    def _on_memory_clear(self, scope: str):
        """Clear one memory scope."""
        if self._client is None or not hasattr(self._client, "clear_memory"):
            return
        try:
            result = self._client.clear_memory(scope)
        except Exception as exc:
            self.toast.show_message(f"Failed to clear memory: {exc}", kind="error")
            return
        if isinstance(result, dict) and "error" in result:
            self.toast.show_message(str(result["error"]), kind="error")
            return
        message = str(result.get("message", "Cleared remembered items.")) if isinstance(result, dict) else "Cleared remembered items."
        self.toast.show_message(message, kind="warn")
        self._refresh_memory_snapshot()

    def set_model_visible(self, visible: bool):
        """Set model visible."""
        if self.model_window is not None:
            self.model_window.show() if visible else self.model_window.hide()
        self.model_visibility_changed.emit(bool(visible))

    def set_speechtospeech_enabled(self, enabled: bool):
        """Set speechtospeech enabled."""
        requested = bool(enabled)
        resolved = requested

        if self._client is not None and hasattr(self._client, "set_speech_to_speech_enabled"):
            try:
                result = self._client.set_speech_to_speech_enabled(requested)
            except Exception as exc:
                self.toast.show_message(f"Failed to update STS setting: {exc}", kind="error")
                result = {"error": str(exc)}

            if isinstance(result, dict) and "error" in result:
                self.toast.show_message(
                    f"Failed to update STS setting: {result['error']}",
                    kind="error",
                )
                resolved = self.speechtospeech_enabled
            elif isinstance(result, dict) and "enabled" in result:
                resolved = bool(result.get("enabled"))

        self.speechtospeech_enabled = bool(resolved)

        if hasattr(self, "_toggle_sts") and self._toggle_sts.isChecked() != self.speechtospeech_enabled:
            from PyQt6.QtCore import QSignalBlocker
            blocker = QSignalBlocker(self._toggle_sts)
            self._toggle_sts.setChecked(self.speechtospeech_enabled)
            del blocker

        self.speechtospeech_enabled_changed.emit(self.speechtospeech_enabled)

    def set_open_app_confirmation_enabled(self, enabled: bool):
        """Set whether opening apps requires confirmation."""
        requested = bool(enabled)
        resolved = requested

        if self._client is not None and hasattr(
            self._client, "set_open_app_confirmation_enabled"
        ):
            try:
                result = self._client.set_open_app_confirmation_enabled(requested)
            except Exception as exc:
                self.toast.show_message(
                    f"Failed to update open-app confirmation: {exc}",
                    kind="error",
                )
                result = {"error": str(exc)}

            if isinstance(result, dict) and "error" in result:
                self.toast.show_message(
                    f"Failed to update open-app confirmation: {result['error']}",
                    kind="error",
                )
                resolved = self.open_app_confirmation_enabled
            elif isinstance(result, dict) and "enabled" in result:
                resolved = bool(result.get("enabled"))

        self.open_app_confirmation_enabled = bool(resolved)

        if (
            hasattr(self, "_toggle_open_app_confirm")
            and self._toggle_open_app_confirm is not None
            and self._toggle_open_app_confirm.isChecked()
            != self.open_app_confirmation_enabled
        ):
            from PyQt6.QtCore import QSignalBlocker

            blocker = QSignalBlocker(self._toggle_open_app_confirm)
            self._toggle_open_app_confirm.setChecked(
                self.open_app_confirmation_enabled
            )
            del blocker

        self.open_app_confirmation_enabled_changed.emit(
            self.open_app_confirmation_enabled
        )

    def set_timer_confirmation_enabled(self, enabled: bool):
        """Set whether timer/alarm actions require confirmation."""
        requested = bool(enabled)
        resolved = requested

        if self._client is not None and hasattr(
            self._client, "set_timer_confirmation_enabled"
        ):
            try:
                result = self._client.set_timer_confirmation_enabled(requested)
            except Exception as exc:
                self.toast.show_message(
                    f"Failed to update timer confirmation: {exc}",
                    kind="error",
                )
                result = {"error": str(exc)}

            if isinstance(result, dict) and "error" in result:
                self.toast.show_message(
                    f"Failed to update timer confirmation: {result['error']}",
                    kind="error",
                )
                resolved = self.timer_confirmation_enabled
            elif isinstance(result, dict) and "enabled" in result:
                resolved = bool(result.get("enabled"))

        self.timer_confirmation_enabled = bool(resolved)

        if (
            hasattr(self, "_toggle_timer_confirm")
            and self._toggle_timer_confirm is not None
            and self._toggle_timer_confirm.isChecked()
            != self.timer_confirmation_enabled
        ):
            from PyQt6.QtCore import QSignalBlocker

            blocker = QSignalBlocker(self._toggle_timer_confirm)
            self._toggle_timer_confirm.setChecked(
                self.timer_confirmation_enabled
            )
            del blocker

        self.timer_confirmation_enabled_changed.emit(self.timer_confirmation_enabled)

    def set_screen_viewing_enabled(self, enabled: bool):
        """Set whether screen-view screenshots are attached to chat requests."""
        requested = bool(enabled)
        resolved = requested

        if self._client is not None and hasattr(
            self._client, "set_screen_viewing_enabled"
        ):
            try:
                result = self._client.set_screen_viewing_enabled(requested)
            except Exception as exc:
                self.toast.show_message(
                    f"Failed to update screen viewing: {exc}",
                    kind="error",
                )
                result = {"error": str(exc)}

            if isinstance(result, dict) and "error" in result:
                self.toast.show_message(
                    f"Failed to update screen viewing: {result['error']}",
                    kind="error",
                )
                resolved = self.screen_viewing_enabled
            elif isinstance(result, dict) and "enabled" in result:
                resolved = bool(result.get("enabled"))

        self.screen_viewing_enabled = bool(resolved)

        if (
            hasattr(self, "_toggle_screen_viewing")
            and self._toggle_screen_viewing is not None
            and self._toggle_screen_viewing.isChecked()
            != self.screen_viewing_enabled
        ):
            from PyQt6.QtCore import QSignalBlocker

            blocker = QSignalBlocker(self._toggle_screen_viewing)
            self._toggle_screen_viewing.setChecked(
                self.screen_viewing_enabled
            )
            del blocker

        self.screen_viewing_enabled_changed.emit(self.screen_viewing_enabled)

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
        except Exception as exc:
            LOGGER.debug("Failed to unsubscribe settings panel theme callback: %s", exc, exc_info=True)
