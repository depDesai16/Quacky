import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal

LOGGER = logging.getLogger(__name__)


class _ApiKeyLoadWorker(QThread):
    loaded = pyqtSignal(bool, str)

    def __init__(self, client):
        """Initialize the instance state."""
        super().__init__()
        self._client = client

    def run(self):
        """Execute the worker task."""
        if self._client is None:
            self.loaded.emit(False, "Client unavailable for API key load.")
            return
        try:
            result = self._client.get_saved_api_key()
        except Exception as exc:
            self.loaded.emit(False, str(exc))
            return

        if isinstance(result, dict) and "error" in result:
            self.loaded.emit(False, str(result.get("error", "Unknown error")))
            return

        has_key = False
        if isinstance(result, dict):
            has_key = bool(result.get("has_key"))
        self.loaded.emit(has_key, "")


class _ApiKeyTestWorker(QThread):
    result_ready = pyqtSignal(bool, str)

    def __init__(self, client, api_key: str):
        """Initialize the instance state."""
        super().__init__()
        self._client = client
        self._api_key = api_key.strip()

    def run(self):
        """Execute the worker task."""
        if self._client is None:
            self.result_ready.emit(False, "Client unavailable for key test.")
            return
        try:
            result = self._client.test_api_key(self._api_key)
        except Exception as exc:
            self.result_ready.emit(False, str(exc))
            return
        if isinstance(result, dict) and "error" in result:
            self.result_ready.emit(False, str(result["error"]))
            return
        ok = bool(result.get("ok")) if isinstance(result, dict) else False
        message = (
            str(result.get("message", "API key test completed."))
            if isinstance(result, dict)
            else "API key test completed."
        )
        self.result_ready.emit(ok, message)


class _ConfirmationSettingsLoadWorker(QThread):
    loaded = pyqtSignal(object, object, object, str)

    def __init__(self, client):
        """Initialize the instance state."""
        super().__init__()
        self._client = client

    def run(self):
        """Execute the worker task."""
        if self._client is None:
            self.loaded.emit(None, None, "Client unavailable for settings load.")
            return

        open_enabled = None
        timer_enabled = None
        screen_enabled = None
        errors: list[str] = []

        try:
            if hasattr(self._client, "get_open_app_confirmation_settings"):
                result = self._client.get_open_app_confirmation_settings()
                if isinstance(result, dict) and "enabled" in result:
                    open_enabled = bool(result.get("enabled"))
        except Exception as exc:
            errors.append(str(exc))

        try:
            if hasattr(self._client, "get_timer_confirmation_settings"):
                result = self._client.get_timer_confirmation_settings()
                if isinstance(result, dict) and "enabled" in result:
                    timer_enabled = bool(result.get("enabled"))
        except Exception as exc:
            errors.append(str(exc))

        try:
            if hasattr(self._client, "get_screen_viewing_settings"):
                result = self._client.get_screen_viewing_settings()
                if isinstance(result, dict) and "enabled" in result:
                    screen_enabled = bool(result.get("enabled"))
        except Exception as exc:
            errors.append(str(exc))

        self.loaded.emit(
            open_enabled,
            timer_enabled,
            screen_enabled,
            "; ".join(errors),
        )


class SettingsController(QObject):
    saved_api_key_loaded = pyqtSignal(bool, str)
    confirmation_settings_loaded = pyqtSignal(object, object, object, str)
    api_key_test_result = pyqtSignal(bool, str)
    api_key_test_started = pyqtSignal()
    api_key_test_finished = pyqtSignal()

    def __init__(self, client, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._client = client
        self._load_worker: _ApiKeyLoadWorker | None = None
        self._confirmation_worker: _ConfirmationSettingsLoadWorker | None = None
        self._test_worker: _ApiKeyTestWorker | None = None

    def refresh_saved_api_key_async(self):
        """Handle refresh saved api key async."""
        if self._load_worker is not None:
            return
        worker = _ApiKeyLoadWorker(self._client)
        worker.loaded.connect(self._on_saved_api_key_loaded)
        worker.finished.connect(self._on_load_finished)
        self._load_worker = worker
        worker.start()

    def refresh_confirmation_settings_async(self):
        """Load confirmation toggle states without blocking the UI thread."""
        if self._confirmation_worker is not None:
            return
        worker = _ConfirmationSettingsLoadWorker(self._client)
        worker.loaded.connect(self._on_confirmation_settings_loaded)
        worker.finished.connect(self._on_confirmation_finished)
        self._confirmation_worker = worker
        worker.start()

    def save_api_key(self, key: str) -> tuple[bool, str]:
        """Save api key."""
        if self._client is None:
            return False, "Client unavailable for save."
        try:
            result = self._client.save_api_key(key)
        except Exception as exc:
            return False, str(exc)
        if isinstance(result, dict) and "error" in result:
            return False, str(result["error"])
        return True, "API key saved locally via backend."

    def remove_api_key(self) -> tuple[bool, str]:
        """Remove api key."""
        if self._client is None:
            return False, "Client unavailable for remove."
        try:
            result = self._client.remove_api_key()
        except Exception as exc:
            return False, str(exc)
        if isinstance(result, dict) and "error" in result:
            return False, str(result["error"])
        return True, "Stored API key removed."

    def test_api_key_async(self, key: str) -> bool:
        """Handle test api key async."""
        if self._test_worker is not None:
            return False
        worker = _ApiKeyTestWorker(self._client, key)
        worker.result_ready.connect(self.api_key_test_result)
        worker.finished.connect(self._on_test_finished)
        self._test_worker = worker
        self.api_key_test_started.emit()
        worker.start()
        return True

    def is_api_key_test_running(self) -> bool:
        """Return whether is api key test running."""
        return self._test_worker is not None

    def _on_saved_api_key_loaded(self, has_key: bool, error: str):
        """Handle saved api key loaded callbacks."""
        self.saved_api_key_loaded.emit(has_key, error)

    def _on_load_finished(self):
        """Handle load finished callbacks."""
        if self._load_worker is None:
            return
        self._load_worker.deleteLater()
        self._load_worker = None

    def _on_confirmation_settings_loaded(self, open_enabled, timer_enabled, screen_enabled, error: str):
        """Handle confirmation settings loaded callbacks."""
        self.confirmation_settings_loaded.emit(open_enabled, timer_enabled, screen_enabled, error)

    def _on_confirmation_finished(self):
        """Handle confirmation settings worker completion."""
        if self._confirmation_worker is None:
            return
        self._confirmation_worker.deleteLater()
        self._confirmation_worker = None

    def _on_test_finished(self):
        """Handle test finished callbacks."""
        if self._test_worker is None:
            return
        self._test_worker.deleteLater()
        self._test_worker = None
        self.api_key_test_finished.emit()

    def shutdown(self):
        """Handle shutdown."""
        if self._load_worker is not None:
            try:
                self._load_worker.requestInterruption()
                self._load_worker.quit()
                self._load_worker.wait(300)
            except Exception as exc:
                LOGGER.debug("Failed to stop API-key load worker cleanly: %s", exc, exc_info=True)
            self._load_worker = None

        if self._confirmation_worker is not None:
            try:
                self._confirmation_worker.requestInterruption()
                self._confirmation_worker.quit()
                self._confirmation_worker.wait(300)
            except Exception as exc:
                LOGGER.debug("Failed to stop confirmation worker cleanly: %s", exc, exc_info=True)
            self._confirmation_worker = None

        if self._test_worker is not None:
            try:
                self._test_worker.requestInterruption()
                self._test_worker.quit()
                self._test_worker.wait(300)
            except Exception as exc:
                LOGGER.debug("Failed to stop API-key test worker cleanly: %s", exc, exc_info=True)
            self._test_worker = None
