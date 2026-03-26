import threading

from PyQt6.QtCore import QObject, pyqtSignal

from backend.client import QuackyClient

STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_THINKING = "thinking"
STATE_SPEAKING = "speaking"


class SpeechToSpeechController(QObject):
    """
    Dedicated speech-to-speech runtime for the STS panel.
    This is intentionally isolated from the chat mic button pipeline.
    """

    state_changed = pyqtSignal(str)
    transcript_line = pyqtSignal(str, str)  # text, role(user|assistant)
    error_occurred = pyqtSignal(str)
    audio_playback_requested = pyqtSignal(bytes, str)  # audio_bytes, mime_type

    def __init__(self, client: QuackyClient, chat_id: str, parent=None):
        super().__init__(parent)
        self._client = client
        self._chat_id = chat_id
        self._stt = None
        self._enabled = True
        self._running = False

        self._lock = threading.RLock()
        self._playback_waiter: threading.Event | None = None
        self._prewarm_thread: threading.Thread | None = None

    def set_enabled(self, enabled: bool):
        self._enabled = bool(enabled)
        if not self._enabled:
            self.stop()

    def start(self) -> bool:
        if not self._enabled:
            self.error_occurred.emit("Speech-to-speech is disabled in Settings.")
            self.state_changed.emit(STATE_IDLE)
            return False

        with self._lock:
            self._running = True
        self.state_changed.emit(STATE_LISTENING)

        try:
            stt = self._ensure_stt()
            if not stt.is_listening:
                stt.start()
            elif hasattr(stt, "set_capture_enabled"):
                stt.set_capture_enabled(True)
        except Exception as exc:
            with self._lock:
                self._running = False
            self.error_occurred.emit(f"Speech-to-speech start failed: {exc}")
            self.state_changed.emit(STATE_IDLE)
            return False

        return True

    def stop(self):
        with self._lock:
            self._running = False
        self._release_playback_waiter()

        stt = self._stt
        if stt is None:
            self.state_changed.emit(STATE_IDLE)
            return

        try:
            if hasattr(stt, "set_capture_enabled"):
                stt.set_capture_enabled(False)
            elif stt.is_listening:
                stt.shutdown()
        except Exception as exc:
            self.error_occurred.emit(f"Speech-to-speech stop fallback: {exc}")
            try:
                if stt.is_listening:
                    stt.shutdown()
            except Exception:
                pass
        finally:
            self.state_changed.emit(STATE_IDLE)

    def shutdown(self):
        with self._lock:
            self._running = False
        self._release_playback_waiter()

        stt = self._stt
        self._stt = None
        if stt is None:
            self.state_changed.emit(STATE_IDLE)
            return

        try:
            if stt.is_listening:
                stt.shutdown()
        except Exception:
            pass
        self.state_changed.emit(STATE_IDLE)

    def notify_audio_playback_finished(self):
        self._release_playback_waiter()

    def prewarm_async(self):
        """Prepare STT instance ahead of Start so first click feels instant."""
        if not self._enabled or self._stt is not None:
            return
        with self._lock:
            if self._prewarm_thread is not None and self._prewarm_thread.is_alive():
                return
            self._prewarm_thread = threading.Thread(
                target=self._prewarm_worker,
                name="sts-prewarm",
                daemon=True,
            )
            self._prewarm_thread.start()

    def _prewarm_worker(self):
        try:
            self._ensure_stt()
        except Exception:
            # Prewarm is best-effort; Start still handles errors visibly.
            pass
        finally:
            with self._lock:
                self._prewarm_thread = None

    def _ensure_stt(self):
        if self._stt is not None:
            return self._stt

        from backend.interact.speechToText.quacky_stt import QuackySpeechToText

        stt = QuackySpeechToText(require_wake_word=False)
        stt.set_callback(self._handle_command)
        self._stt = stt
        return stt

    def _emit_state_after_response(self):
        with self._lock:
            running = self._running
        self.state_changed.emit(STATE_LISTENING if running else STATE_IDLE)

    def _handle_command(self, command: str) -> str:
        text = command.strip()
        if not text:
            self._emit_state_after_response()
            return ""

        self.transcript_line.emit(text, "user")
        self.state_changed.emit(STATE_THINKING)

        result = self._send_sts_request(text)
        if result is None:
            self._emit_state_after_response()
            return ""

        if isinstance(result, dict) and "error" in result:
            self.error_occurred.emit(str(result.get("error", "Unknown STS error")))
            self._emit_state_after_response()
            return ""

        reply = str(result.get("text", "") if isinstance(result, dict) else "").strip()
        if reply:
            self.transcript_line.emit(reply, "assistant")

        tts_error = str(result.get("tts_error", "")).strip() if isinstance(result, dict) else ""
        audio_bytes = self._client.decode_audio_bytes(result) if isinstance(result, dict) else None

        if tts_error:
            self.error_occurred.emit(f"TTS: {tts_error}")

        if audio_bytes:
            mime_type = str(result.get("audio_mime_type", "audio/mpeg"))
            self.state_changed.emit(STATE_SPEAKING)
            self._wait_for_playback(audio_bytes, mime_type)

        self._emit_state_after_response()
        return reply

    def _send_sts_request(self, text: str):
        """
        Prefer dedicated STS endpoint, but gracefully fall back to generic chat
        message with `tts=True` for older backend versions.
        """
        try:
            result = self._client.send_speech_to_speech_message(self._chat_id, text)
        except Exception as exc:
            self.error_occurred.emit(f"Speech-to-speech request failed: {exc}")
            return None

        err = str(result.get("error", "")).strip().lower() if isinstance(result, dict) else ""
        if err and "not found" in err:
            try:
                return self._client.send_message(self._chat_id, text, tts=True)
            except Exception as exc:
                self.error_occurred.emit(f"STS fallback request failed: {exc}")
                return None
        return result

    def _wait_for_playback(self, audio_bytes: bytes, mime_type: str):
        waiter = threading.Event()
        with self._lock:
            self._playback_waiter = waiter
        self.audio_playback_requested.emit(audio_bytes, mime_type)
        waiter.wait(timeout=30.0)
        with self._lock:
            if self._playback_waiter is waiter:
                self._playback_waiter = None

    def _release_playback_waiter(self):
        with self._lock:
            waiter = self._playback_waiter
            self._playback_waiter = None
        if waiter is not None:
            waiter.set()
