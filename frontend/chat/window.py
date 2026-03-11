import os
import sys

CHAT_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(CHAT_DIR)
ROOT_DIR     = os.path.dirname(FRONTEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtCore    import (Qt, QThread, pyqtSignal, QObject,
                              QPropertyAnimation, QEasingCurve, QEvent, QTimer,
                              QByteArray, QBuffer, QIODevice, QUrl)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QGraphicsOpacityEffect)
from PyQt6.QtGui     import QKeyEvent, QCursor
from PyQt6.QtCore    import QSettings, QPoint, QSignalBlocker
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from theme          import ThemeManager
from draw_icon      import draw_icon
from .model_window import ModelWindow
from backend.client import QuackyClient

from widgets.card_widget   import CardWidget
from widgets.header_bar    import HeaderBar
from widgets.chat_timeline import ChatTimeline
from widgets.composer      import Composer
from widgets.icon_buttons  import MicButton, SendButton
from widgets.toast         import Toast

from settings import SettingsPanel

MAX_WINDOW_W = 1040
MIN_WINDOW_W = 600
MIN_WINDOW_H = 660


class ChatWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, client: QuackyClient, chat_id: str, message: str):
        """Initialize the instance state."""
        super().__init__()
        self._client  = client
        self._chat_id = chat_id
        self._message = message

    def run(self):
        """Execute the worker task."""
        result = self._client.send_message(self._chat_id, self._message)
        if "error" in result:
            self.error_occurred.emit(result["error"])
        else:
            self.response_ready.emit(result.get("text", ""))



class StreamingChatWorker(QThread):
    chunk_received = pyqtSignal(str)
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, client: QuackyClient, chat_id: str, message: str):
        """Initialize the instance state."""
        super().__init__()
        self._client  = client
        self._chat_id = chat_id
        self._message = message

    def run(self):
        """Execute the worker task."""
        if hasattr(self._client, 'stream_message'):
            try:
                full = ""
                for chunk in self._client.stream_message(
                        self._chat_id, self._message):
                    if isinstance(chunk, dict):
                        text = chunk.get(
                            'text', chunk.get('chunk', chunk.get('delta', ''))
                        )
                    else:
                        text = str(chunk)
                    if text:
                        full += text
                        self.chunk_received.emit(text)
                self.response_ready.emit(full)
                return
            except Exception:
                pass

        result = self._client.send_message(self._chat_id, self._message)
        if "error" in result:
            self.error_occurred.emit(result["error"])
            return
        text = result.get("text", "")
        if text:
            self.chunk_received.emit(text)
        self.response_ready.emit(text)



class STTBridge(QObject):
    command_received = pyqtSignal(str)
    response_ready   = pyqtSignal(str)
    error_occurred   = pyqtSignal(str)

    def __init__(self, client: QuackyClient, chat_id: str):
        """Initialize the instance state."""
        super().__init__()
        self._client  = client
        self._chat_id = chat_id

    def handle_command(self, command: str) -> str:
        """Handle handle command."""
        self.command_received.emit(command)
        result = self._client.send_message(self._chat_id, command, tts=False)
        if "error" in result:
            self.error_occurred.emit(result["error"])
            return f"[Error] {result['error']}"
        text = result.get("text", "")
        self.response_ready.emit(text)
        return text



class QuackyWindow(QWidget):

    def __init__(self, client: QuackyClient, chat_id: str):
        """Initialize the instance state."""
        super().__init__()

        self._client                = client
        self._chat_id               = chat_id
        self._active_worker         = None
        self._stt                   = None
        self._stt_bridge: STTBridge | None = None
        self._stt_capture_enabled   = False
        self._sts_controller        = None
        self._sts_audio_player: QMediaPlayer | None = None
        self._sts_audio_output: QAudioOutput | None = None
        self._sts_audio_buffer: QBuffer | None = None
        self._sts_audio_data: QByteArray | None = None
        self._sts_tts_available     = True
        self.speechtospeech_enabled = True
        self._drag_pos:        QPoint | None = None
        self._resize_dir:       str    | None = None
        self._resize_start_geo         = None
        self._last_failed_text: str    | None = None
        
        # User profile
        self.current_user = "Guest"
        
        # Initialize face recognition manager early (before camera)
        from camera.face_recognition import FaceRecognitionManager
        self.face_recognition = FaceRecognitionManager()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowTitle("Quacky")
        self.setObjectName("quacky-main-window")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(MIN_WINDOW_W, MIN_WINDOW_H)
        self._screen_hooked = False
        self._resize_tracking_installed = False
        self._apply_wm_size_hints()
        self.resize(620, 740)

        ThemeManager.load()
        self._restore_geometry()
        self._load_speech_to_speech_settings()

        self.model_window = None
        try:
            self.model_window = ModelWindow()
            _screen = QApplication.primaryScreen()
            if _screen is not None:
                _sg = _screen.availableGeometry()
                self.model_window.move(
                    _sg.x() + _sg.width() - self.model_window.width() - 20,
                    _sg.y() + 88,
                )
            else:
                self.model_window.move(1040, 88)
        except Exception:
            self.model_window = None

        self._theme_fade_overlay = None
        self._theme_fade_anim    = None

        self._build_ui()
        self._install_resize_cursor_tracking()
        ThemeManager.subscribe(self._on_theme_changed)

    def _load_speech_to_speech_settings(self):
        """Load server-side STS defaults when available."""
        if not hasattr(self._client, "get_speech_to_speech_settings"):
            return
        try:
            result = self._client.get_speech_to_speech_settings()
        except Exception:
            return

        if not isinstance(result, dict):
            return

        if "enabled" in result:
            self.speechtospeech_enabled = bool(result.get("enabled"))
        if "tts_available" in result:
            self._sts_tts_available = bool(result.get("tts_available"))


    def _build_ui(self):
        """Build ui."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        self.card = CardWidget()
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        self.header = HeaderBar(icon=draw_icon(), parent=self.card)
        self.header.minimize_clicked.connect(self.hide)
        self.header.close_clicked.connect(QApplication.instance().quit)
        if hasattr(self.header, "user_chip_clicked"):
            self.header.user_chip_clicked.connect(self._show_user_menu)
        self.header.settings_clicked.connect(self._show_settings)
        self.header.back_clicked.connect(self._show_chat)
        cl.addWidget(self.header)
        
        # Create stacked widget to hold chat, camera, and settings views
        from PyQt6.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        
        # Chat view (existing timeline)
        self._chat_container = QWidget()
        self._chat_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        chat_inner = QVBoxLayout(self._chat_container)
        chat_inner.setContentsMargins(0, 0, 0, 0)
        chat_inner.setSpacing(0)
        
        self.timeline = ChatTimeline(draw_icon_fn=draw_icon, parent=self._chat_container)
        self._wire_suggestions()
        chat_inner.addWidget(self.timeline, 1)
        
        # Camera view
        from camera.camera_view import CameraView
        self.camera_view = CameraView(parent=self.card)
        self.camera_view.back_requested.connect(self._toggle_camera_view)
        
        # Don't connect automatic user recognition - only use Face ID dialog
        # self.camera_view.user_recognized.connect(self._on_user_profile_changed)
        
        # Settings panel
        self._settings_container = SettingsPanel(
            model_window=self.model_window,
            speechtospeech_enabled=self.speechtospeech_enabled,
            toast_callback=self._show_settings_toast,
            client=self._client,
            parent=self.card,
        )
        self._settings_container.model_visibility_changed.connect(self.set_model_visible)
        self._settings_container.speechtospeech_enabled_changed.connect(
            self.set_speechtospeech_enabled
        )
        
        # Add views to stacked widget
        self.stacked_widget.addWidget(self._chat_container)     # index 0
        self.stacked_widget.addWidget(self.camera_view)         # index 1
        self.stacked_widget.addWidget(self._settings_container) # index 2

        # Speech-to-speech panel/runtime (isolated from chat mic pipeline)
        from chat.speech_to_speech import SpeechToSpeechPanel, SpeechToSpeechController
        self._sts_panel = SpeechToSpeechPanel(parent=self.card)
        self._sts_panel.back_requested.connect(self._hide_sts_panel)
        self._sts_panel.start_requested.connect(self._on_sts_start)
        self._sts_panel.stop_requested.connect(self._on_sts_stop)

        self._sts_controller = SpeechToSpeechController(
            client=self._client,
            chat_id=self._chat_id,
            parent=self,
        )
        self._sts_controller.set_enabled(self.speechtospeech_enabled)
        self._sts_controller.state_changed.connect(self._sts_panel.set_state)
        self._sts_controller.transcript_line.connect(self._sts_panel.add_transcript_line)
        self._sts_controller.error_occurred.connect(self._on_sts_error)
        self._sts_controller.audio_playback_requested.connect(self._play_sts_audio)

        self.stacked_widget.addWidget(self._sts_panel)          # index 3
        
        cl.addWidget(self.stacked_widget, 1)
        self._init_sts_audio_player()

        self.mic_btn  = MicButton()
        self.send_btn = SendButton()
        from widgets.icon_buttons import SpeechToSpeechButton
        self.sts_btn  = SpeechToSpeechButton()
        self.composer = Composer(
            mic_button=self.mic_btn,
            send_button=self.send_btn,
            sts_button=self.sts_btn,
            parent=self.card,
        )
        self.composer.input_field.send_requested.connect(self.send_message)
        self.send_btn.clicked.connect(self.send_message)
        self.sts_btn.clicked.connect(self._show_sts_panel)
        self._update_sts_button_hint()
        self.composer.plus_btn.camera_clicked.connect(self._toggle_camera_view)
        self.composer.plus_btn.shortcuts_clicked.connect(self._show_shortcuts_panel)
        self.composer.input_field.textChanged.connect(self._update_send_btn)
        self.composer.input_field.textChanged.connect(self._update_toast_anchor)
        self.mic_btn.toggled.connect(self.on_mic_toggle)
        cl.addWidget(self.composer)

        root.addWidget(self.card)
        self.toast = Toast(self.card)
        self._update_toast_anchor()
    
    def _toggle_camera_view(self):
        """Toggle the camera panel on/off."""
        is_camera = self.stacked_widget.currentIndex() == 1
        if is_camera:
            # Return to chat
            self.stacked_widget.setCurrentIndex(0)
            self.composer.show()
            self.composer.plus_btn.set_camera_active(False)
        else:
            # Show camera
            self.stacked_widget.setCurrentIndex(1)
            self.composer.hide()
            self.composer.plus_btn.set_camera_active(True)
    
    def _on_user_profile_changed(self, name, confidence):
        """Handle user profile change from face recognition"""
        if name != "Unknown" and name != self.current_user:
            self.current_user = name
            # Update header to show current user
            if hasattr(self.header, "set_user"):
                self.header.set_user(name)
            # Update window title
            self.setWindowTitle(f"Quacky - {name}")
            # Show notification in chat
            self.timeline.add_system_message(
                f'<span style="color:#00d4ff;">Welcome back, {name}! '
                f'Profile switched from Guest.</span>'
            )
        elif name == "Unknown" and self.current_user != "Guest":
            self.current_user = "Guest"
            if hasattr(self.header, "set_user"):
                self.header.set_user("Guest")
            self.setWindowTitle("Quacky")
            self.timeline.add_system_message(
                '<span style="color:#888;">Switched to Guest mode.</span>'
            )
    
    def _show_user_menu(self):
        """Show user profile menu"""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {ThemeManager.tokens()['bg.elevated']};
                border: 1px solid {ThemeManager.tokens()['border.strong']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                color: {ThemeManager.tokens()['text.primary']};
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background: {ThemeManager.tokens()['accent.subtleBg']};
                color: {ThemeManager.tokens()['accent.primary']};
            }}
        """)
        
        # Get registered users count
        registered_users = self.face_recognition.get_registered_users()
        user_count = len(registered_users)
        
        # Current user indicator
        current_text = f"Current: {self.current_user}"
        current_action = menu.addAction(f"👤 {current_text}")
        current_action.setEnabled(False)  # Just for display
        
        menu.addSeparator()
        
        # Switch Profile - Face ID style
        if user_count > 0:
            switch_action = menu.addAction("🔓 Switch Profile (Face ID)")
            switch_action.triggered.connect(self._start_face_id_switch)
        else:
            no_users_action = menu.addAction("⚠️  No registered users")
            no_users_action.setEnabled(False)
        
        # Register new user
        register_action = menu.addAction("📸 Register New Face...")
        register_action.triggered.connect(self._register_new_user)
        
        # Guest mode option
        if self.current_user != "Guest":
            menu.addSeparator()
            guest_action = menu.addAction("👤 Switch to Guest")
            guest_action.triggered.connect(lambda: self._switch_to_user("Guest"))
        
        # Show menu below the user chip
        if hasattr(self.header, "user_chip"):
            chip_pos = self.header.user_chip.mapToGlobal(
                self.header.user_chip.rect().bottomLeft()
            )
        else:
            chip_pos = self.header.mapToGlobal(self.header.rect().bottomLeft())
        menu.exec(chip_pos)
    
    def _switch_to_user(self, user_name):
        """Manually switch to a user"""
        if user_name != self.current_user:
            self.current_user = user_name
            if hasattr(self.header, "set_user"):
                self.header.set_user(user_name)
            if user_name == "Guest":
                self.setWindowTitle("Quacky")
                self.timeline.add_system_message(
                    '<span style="color:#888;">Switched to Guest mode.</span>'
                )
            else:
                self.setWindowTitle(f"Quacky - {user_name}")
                self.timeline.add_system_message(
                    f'<span style="color:#00d4ff;">Switched to {user_name}\'s profile.</span>'
                )
    
    def _register_new_user(self):
        """Show registration dialog"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Switch to camera view
        if self.stacked_widget.currentIndex() != 1:
            self._toggle_camera_view()
    
    def _start_face_id_switch(self):
        """Start Face ID authentication to switch profiles"""
        from camera.face_id_dialog import FaceIDDialog
        
        # Stop camera if it's running
        was_on_camera = self.stacked_widget.currentIndex() == 1
        if was_on_camera and hasattr(self, 'camera_view') and self.camera_view.camera_thread:
            self.camera_view.stop_camera()
            QTimer.singleShot(200, lambda: self._show_face_id_dialog(was_on_camera))
        else:
            self._show_face_id_dialog(was_on_camera)
    
    def _show_face_id_dialog(self, was_on_camera):
        """Show the Face ID dialog after camera is released"""
        from camera.face_id_dialog import FaceIDDialog
        
        # Create and show Face ID dialog
        dialog = FaceIDDialog(self.face_recognition, self)
        dialog.user_authenticated.connect(self._on_face_id_success)
        result = dialog.exec()
        
        # Restart camera tab if it was on camera view
        if was_on_camera:
            QTimer.singleShot(200, self.camera_view.start_camera)
    
    def _on_face_id_success(self, name, confidence):
        """Handle successful Face ID authentication"""
        if name != self.current_user:
            self.current_user = name
            if hasattr(self.header, "set_user"):
                self.header.set_user(name)
            self.setWindowTitle(f"Quacky - {name}")
            self.timeline.add_system_message(
                f'<span style="color:#00d4ff;">✓ Authenticated as {name} '
                f'({confidence*100:.0f}% confidence)</span>'
            )


    def _show_settings_toast(self, message: str, kind: str):
        """Show settings toast."""
        if hasattr(self, "toast"):
            self.toast.show_message(message, kind=kind)

    def _show_settings(self):
        """Show settings."""
        self._settings_container.prepare_for_show()
        self.stacked_widget.setCurrentIndex(2)  # Settings is index 2
        self.composer.hide()
        self.composer.plus_btn.set_camera_active(False)
        self.header.enter_settings_mode()

    def _show_chat(self):
        """Show chat."""
        self.stacked_widget.setCurrentIndex(0)  # Chat is index 0
        self.composer.show()
        self.composer.plus_btn.set_camera_active(False)
        self.header.exit_settings_mode()
        self._update_toast_anchor()

    def _wire_suggestions(self):
        """Handle wire suggestions."""
        if self.timeline._empty_widget:
            self.timeline._empty_widget.suggestion_clicked.connect(
                self._on_suggestion
            )

    def _on_suggestion(self, text: str):
        """Handle suggestion callbacks."""
        self.composer.input_field.setPlainText(text)
        self.composer.input_field.setFocus()


    def set_model_visible(self, visible: bool):
        """Set model visible."""
        if self.model_window is None:
            return
        self.model_window.show() if visible else self.model_window.hide()

    def set_speechtospeech_enabled(self, enabled: bool):
        """Set speechtospeech enabled."""
        self.speechtospeech_enabled = bool(enabled)
        self._update_sts_button_hint()
        if self._sts_controller is not None:
            self._sts_controller.set_enabled(self.speechtospeech_enabled)
        if (not self.speechtospeech_enabled and hasattr(self, "stacked_widget")
                and self.stacked_widget.currentIndex() == 3):
            self._hide_sts_panel()

    def _update_sts_button_hint(self):
        """Keep STS button clickable, but communicate current availability."""
        if not hasattr(self, "sts_btn"):
            return
        self.sts_btn.setEnabled(True)
        if self.speechtospeech_enabled:
            self.sts_btn.setToolTip("Open speech-to-speech")
        else:
            self.sts_btn.setToolTip("Speech-to-speech is off. Click to enable and open.")

    def _ensure_sts_enabled(self) -> bool:
        """Enable STS in backend/settings if currently disabled."""
        if self.speechtospeech_enabled:
            return True
        if not hasattr(self._client, "set_speech_to_speech_enabled"):
            self._show_settings_toast(
                "Speech-to-speech is disabled and cannot be enabled from client.",
                "error",
            )
            return False
        try:
            result = self._client.set_speech_to_speech_enabled(True)
        except Exception as exc:
            self._show_settings_toast(
                f"Failed to enable speech-to-speech: {exc}",
                "error",
            )
            return False
        if isinstance(result, dict) and "error" in result:
            self._show_settings_toast(
                f"Failed to enable speech-to-speech: {result['error']}",
                "error",
            )
            return False
        enabled = bool(result.get("enabled", True)) if isinstance(result, dict) else True
        if not enabled:
            self._show_settings_toast(
                "Speech-to-speech remains disabled on server.",
                "error",
            )
            return False
        self.set_speechtospeech_enabled(True)
        return True

    def _init_sts_audio_player(self):
        """Initialize audio playback for speech-to-speech responses."""
        self._sts_audio_output = QAudioOutput(self)
        self._sts_audio_output.setVolume(1.0)

        self._sts_audio_player = QMediaPlayer(self)
        self._sts_audio_player.setAudioOutput(self._sts_audio_output)
        self._sts_audio_player.mediaStatusChanged.connect(self._on_sts_audio_status)
        self._sts_audio_player.errorOccurred.connect(self._on_sts_audio_error)

    def _play_sts_audio(self, audio_bytes: bytes, mime_type: str):
        """Play backend-generated TTS audio for STS."""
        if self._sts_audio_player is None:
            if self._sts_controller is not None:
                self._sts_controller.notify_audio_playback_finished()
            return
        if not audio_bytes:
            if self._sts_controller is not None:
                self._sts_controller.notify_audio_playback_finished()
            return

        try:
            if self._sts_audio_buffer is not None and self._sts_audio_buffer.isOpen():
                self._sts_audio_buffer.close()

            self._sts_audio_data = QByteArray(audio_bytes)
            self._sts_audio_buffer = QBuffer(self)
            self._sts_audio_buffer.setData(self._sts_audio_data)
            self._sts_audio_buffer.open(QIODevice.OpenModeFlag.ReadOnly)

            suffix = "mp3" if "mpeg" in (mime_type or "").lower() else "wav"
            self._sts_audio_player.stop()
            self._sts_audio_player.setSourceDevice(
                self._sts_audio_buffer,
                QUrl(f"speech_to_speech.{suffix}"),
            )
            self._sts_audio_player.play()
        except Exception as exc:
            self._on_sts_error(f"Audio playback failed: {exc}")
            if self._sts_controller is not None:
                self._sts_controller.notify_audio_playback_finished()

    def _on_sts_audio_status(self, status: QMediaPlayer.MediaStatus):
        """Release STS worker waiters once playback ends/fails."""
        if status in (
            QMediaPlayer.MediaStatus.EndOfMedia,
            QMediaPlayer.MediaStatus.InvalidMedia,
            QMediaPlayer.MediaStatus.NoMedia,
        ):
            if self._sts_audio_buffer is not None and self._sts_audio_buffer.isOpen():
                self._sts_audio_buffer.close()
            if self._sts_controller is not None:
                self._sts_controller.notify_audio_playback_finished()

    def _on_sts_audio_error(self, error: QMediaPlayer.Error, error_string: str):
        """Surface STS audio playback errors without breaking chat mic flow."""
        if error == QMediaPlayer.Error.NoError:
            return
        msg = error_string or str(error)
        self._on_sts_error(f"Audio playback error: {msg}")
        if self._sts_controller is not None:
            self._sts_controller.notify_audio_playback_finished()

    def shutdown(self):
        """Handle shutdown."""
        if hasattr(self, "_settings_container"):
            self._settings_container.shutdown()
        if self._sts_controller is not None:
            self._sts_controller.shutdown()
        if self._sts_audio_player is not None:
            self._sts_audio_player.stop()
        self._stop_stt(full_shutdown=True)


    def send_message(self):
        """Handle send message."""
        text = self.composer.text().strip()
        if not text:
            return
        self.composer.clear()
        self._dispatch_text_message(text)

    def _dispatch_text_message(self, text: str):
        """Handle dispatch text message."""
        self._last_failed_text = text
        self._append_user(text)
        self._set_input_busy(True)

        worker = StreamingChatWorker(self._client, self._chat_id, text)
        worker.chunk_received.connect(self._on_chunk)
        worker.response_ready.connect(self._on_stream_complete)
        worker.error_occurred.connect(self._on_error)
        worker.finished.connect(lambda: self._set_input_busy(False))
        self._active_worker = worker
        worker.start()


    def on_mic_toggle(self, listening: bool):
        """Handle mic toggle callbacks."""
        if listening == self._stt_capture_enabled and self._stt is not None:
            return
        if listening:
            self.mic_btn.setToolTip("ListeningÃ¢â‚¬Â¦ (click to stop)")
            self._start_stt()
        else:
            self.mic_btn.setToolTip("Click to start voice input")
            self._stop_stt()

    def _start_stt(self):
        """Handle start stt."""
        try:
            from backend.interact.speechToText.quacky_stt import QuackySpeechToText
        except ImportError:
            self._append_system("Ã¢Å¡Â  quacky_stt not found Ã¢â‚¬â€ voice input unavailable.")
            self._set_mic_checked(False)
            return

        if self._stt is None:
            try:
                self._stt = QuackySpeechToText(require_wake_word=False)
            except Exception as exc:
                self._append_system(f"Ã¢Å¡Â  Microphone init failed: {exc}")
                self._set_mic_checked(False)
                return

            self._stt_bridge = STTBridge(self._client, self._chat_id)
            self._stt_bridge.command_received.connect(self._on_stt_command)
            self._stt_bridge.response_ready.connect(self._on_stt_response)
            self._stt_bridge.error_occurred.connect(self._on_error)
            self._stt.set_callback(self._stt_bridge.handle_command)

        try:
            if not self._stt.is_listening:
                self._stt.start()
            elif hasattr(self._stt, "set_capture_enabled"):
                self._stt.set_capture_enabled(True)
        except Exception as exc:
            self._append_system(f"Ã¢Å¡Â  Voice input start failed: {exc}")
            self._stt_capture_enabled = False
            self._set_mic_checked(False)
            try:
                if self._stt and self._stt.is_listening:
                    self._stt.shutdown()
            except Exception:
                pass
            self._stt = None
            return

        self._stt_capture_enabled = True

    def _stop_stt(self, full_shutdown: bool = False):
        """Handle stop stt."""
        if not self._stt:
            self._stt_capture_enabled = False
            return

        try:
            if full_shutdown:
                if self._stt.is_listening:
                    self._stt.shutdown()
                self._stt_capture_enabled = False
                return

            if hasattr(self._stt, "set_capture_enabled"):
                self._stt.set_capture_enabled(False)
            elif self._stt.is_listening:
                self._stt.shutdown()
        except Exception as exc:
            self._append_system(f"Ã¢Å¡Â  Voice input stop fallback: {exc}")
            try:
                if self._stt and self._stt.is_listening:
                    self._stt.shutdown()
            except Exception:
                pass
        finally:
            self._stt_capture_enabled = False

    def _set_mic_checked(self, checked: bool):
        """Set mic checked."""
        blocker = QSignalBlocker(self.mic_btn)
        self.mic_btn.setChecked(checked)
        del blocker


    def _on_chunk(self, chunk: str):
        """Handle chunk callbacks."""
        self.timeline.append_stream_chunk(chunk)

    def _on_stream_complete(self, full_text: str):
        """Handle stream complete callbacks."""
        self.timeline.finalize_stream()
        self.header.set_status("responding")
        self._last_failed_text = None

    def _on_stt_command(self, command: str):
        """Handle stt command callbacks."""
        self._append_user(command)
        self._set_input_busy(True)

    def _on_stt_response(self, text: str):
        """Handle stt response callbacks."""
        self._append_quacky(text)
        self._set_input_busy(False)

    def _on_error(self, error: str):
        """Handle error callbacks."""
        self.timeline.finalize_stream()
        self.timeline.hide_thinking()
        self._append_system(f"Ã¢Å¡Â  {error}")
        self._set_input_busy(False)
        if self._last_failed_text:
            self.timeline.show_retry_prompt(self._last_failed_text, self._on_retry)

    def _on_retry(self, text: str):
        """Handle retry callbacks."""
        self.timeline.hide_retry_prompt()
        self._last_failed_text = None
        self._set_input_busy(True)
        worker = StreamingChatWorker(self._client, self._chat_id, text)
        worker.chunk_received.connect(self._on_chunk)
        worker.response_ready.connect(self._on_stream_complete)
        worker.error_occurred.connect(self._on_error)
        worker.finished.connect(lambda: self._set_input_busy(False))
        self._active_worker = worker
        worker.start()


    def _append_user(self, text: str):
        """Handle append user."""
        self.timeline.add_user_message(text)
        self._wire_suggestions()

    def _append_quacky(self, text: str):
        """Handle append quacky."""
        self.timeline.hide_thinking()
        self.timeline.add_assistant_message(text)

    def _append_system(self, html: str):
        """Handle append system."""
        self.timeline.add_system_message(html)

    def _set_input_busy(self, busy: bool):
        """Set input busy."""
        self.composer.set_busy(busy)
        self.send_btn.setEnabled(
            False if busy else bool(self.composer.text().strip())
        )
        if busy:
            self.header.set_status("thinking")
            self.timeline.show_thinking()
        else:
            self.header.set_status("idle")

    def _update_send_btn(self):
        """Update send btn."""
        has_text = bool(self.composer.input_field.toPlainText().strip())
        self.send_btn.setEnabled(has_text)
        self.composer.set_has_text(has_text)
        self._update_toast_anchor()
        QTimer.singleShot(0, self._update_toast_anchor)

    def _show_sts_panel(self):
        """Show speech-to-speech panel."""
        self.stacked_widget.setCurrentIndex(3)
        self.composer.hide()
        self._sts_panel.clear_transcript()
        self._sts_panel.set_state("idle")
        if self._sts_controller is not None:
            self._sts_controller.prewarm_async()

    def _hide_sts_panel(self):
        """Return from S2S panel to chat."""
        self._on_sts_stop()
        self.stacked_widget.setCurrentIndex(0)
        self.composer.show()
        self._update_toast_anchor()

    def _on_sts_start(self):
        """Start dedicated speech-to-speech capture/runtime."""
        self._sts_panel.set_state("listening")
        if not self._ensure_sts_enabled():
            self._sts_panel.set_state("idle")
            return
        if not self._sts_tts_available:
            self._show_settings_toast(
                "TTS is unavailable on server; STS will run in text-response mode.",
                "warn",
            )
        if self._sts_controller is not None:
            self._sts_controller.start()

    def _on_sts_stop(self):
        """S2S stop button pressed."""
        if self._sts_audio_player is not None:
            self._sts_audio_player.stop()
        if self._sts_controller is not None:
            self._sts_controller.stop()
        else:
            self._sts_panel.set_state("idle")

    def _on_sts_error(self, message: str):
        """Handle STS-specific failures and surface them in the STS panel."""
        if hasattr(self, "_sts_panel"):
            self._sts_panel.add_transcript_line(f"Warning: {message}", role="assistant")
        self._show_settings_toast(message, "error")

    def _update_toast_anchor(self):
        """Update toast anchor."""
        if not hasattr(self, 'toast'):
            return
        clearance = self.composer.height() + 8
        self.toast.set_bottom_clearance(clearance)
        timeline_clearance = max(28, int(self.composer.height() * 0.45))
        self.timeline.set_bottom_clearance(timeline_clearance)
        pill_clearance = clearance + 46
        self.timeline.set_new_message_pill_clearance(pill_clearance)


    def _on_theme_changed(self, tokens: dict):
        """Handle theme changed callbacks."""
        if hasattr(self, "_settings_container"):
            self._settings_container.apply_theme(tokens)


    def _install_resize_cursor_tracking(self):
        """Handle install resize cursor tracking."""
        self.setMouseTracking(True)
        if not self._resize_tracking_installed:
            self.installEventFilter(self)
            self.setProperty("_resize_tracking_installed", True)
            self._resize_tracking_installed = True

        for w in self.findChildren(QWidget):
            if bool(w.property("_resize_tracking_installed")):
                continue
            w.setMouseTracking(True)
            w.installEventFilter(self)
            w.setProperty("_resize_tracking_installed", True)

    def _update_resize_cursor(self):
        """Update resize cursor."""
        if self._drag_pos is not None:
            return
        local = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(local):
            self.unsetCursor()
            return
        region = self._hit_region(local)
        cur = self._CURSORS.get(region, Qt.CursorShape.ArrowCursor)
        self.setCursor(cur)

    def eventFilter(self, obj, event):
        """Handle eventfilter."""
        if isinstance(obj, QWidget) and (obj is self or self.isAncestorOf(obj)):
            et = event.type()
            if et == QEvent.Type.ChildAdded:
                child = event.child() if hasattr(event, "child") else None
                if isinstance(child, QWidget):
                    child.setMouseTracking(True)
                    if not bool(child.property("_resize_tracking_installed")):
                        child.installEventFilter(self)
                        child.setProperty("_resize_tracking_installed", True)
            elif et in (
                QEvent.Type.MouseMove,
                QEvent.Type.HoverMove,
                QEvent.Type.Enter,
            ):
                if QApplication.mouseButtons() == Qt.MouseButton.NoButton:
                    self._update_resize_cursor()
            elif et in (QEvent.Type.Leave, QEvent.Type.HoverLeave):
                self._update_resize_cursor()
        return super().eventFilter(obj, event)


    def _clear_theme_overlay(self):
        """Clear theme overlay."""
        anim = self._theme_fade_anim
        if anim is not None:
            try:
                anim.stop()
            except Exception:
                pass
        self._theme_fade_anim = None

        overlay = self._theme_fade_overlay
        if overlay is not None:
            try:
                overlay.hide()
                overlay.deleteLater()
            except Exception:
                pass
        self._theme_fade_overlay = None

    def _toggle_theme_with_transition(self):
        """Toggle theme with transition."""
        self._clear_theme_overlay()

        overlay = QLabel(self)
        overlay.setPixmap(self.grab())
        overlay.setScaledContents(True)
        overlay.setGeometry(self.rect())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        overlay.setStyleSheet("background: transparent;")

        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(1.0)
        overlay.setGraphicsEffect(effect)
        overlay.show()
        overlay.raise_()

        self._theme_fade_overlay = overlay

        ThemeManager.toggle()

        anim = QPropertyAnimation(effect, b"opacity", overlay)
        anim.setDuration(220)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._clear_theme_overlay)
        self._theme_fade_anim = anim
        anim.start()


    def keyPressEvent(self, event: QKeyEvent):
        """Handle the keypress event."""
        mod = event.modifiers()
        key = event.key()

        if mod & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_T:
            self._toggle_theme_with_transition()
            self.toast.show_message(
                f"{ThemeManager.current().capitalize()} theme", kind="success"
            )
            return

        if mod & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_L:
            self.composer.input_field.setFocus()
            return

        if mod & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Slash:
            self._show_shortcuts_panel()
            return

        if key == Qt.Key.Key_Escape:
            if self.composer.text().strip():
                self.composer.clear()
            else:
                self.hide()
            return

        super().keyPressEvent(event)

    EDGE        = 8
    CORNER_GRAB = 24

    def _hit_region(self, pos):
        """Handle hit region."""
        x, y  = pos.x(), pos.y()
        w, h  = self.width(), self.height()
        e     = self.EDGE
        c     = self.CORNER_GRAB

        if x <= c and y <= c:              return 'tl'
        if x >= w - c and y <= c:          return 'tr'
        if x <= c and y >= h - c:          return 'bl'
        if x >= w - c and y >= h - c:      return 'br'

        left  = x <= e
        right = x >= w - e
        top   = y <= e
        bot   = y >= h - e
        if top:   return 't'
        if bot:   return 'b'
        if left:  return 'l'
        if right: return 'r'
        if y <= self.header.height() + 12: return 'drag'
        return None

    _CURSORS = {
        'tl':   Qt.CursorShape.SizeFDiagCursor,
        'br':   Qt.CursorShape.SizeFDiagCursor,
        'tr':   Qt.CursorShape.SizeBDiagCursor,
        'bl':   Qt.CursorShape.SizeBDiagCursor,
        't':    Qt.CursorShape.SizeVerCursor,
        'b':    Qt.CursorShape.SizeVerCursor,
        'l':    Qt.CursorShape.SizeHorCursor,
        'r':    Qt.CursorShape.SizeHorCursor,
        'drag': Qt.CursorShape.ArrowCursor,
    }
    _SYSTEM_RESIZE_EDGES = {
        't':  Qt.Edge.TopEdge,
        'b':  Qt.Edge.BottomEdge,
        'l':  Qt.Edge.LeftEdge,
        'r':  Qt.Edge.RightEdge,
        'tl': Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
        'tr': Qt.Edge.TopEdge | Qt.Edge.RightEdge,
        'bl': Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
        'br': Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
    }

    def _window_handle(self):
        """Return native window handle if available."""
        handle = self.windowHandle()
        if handle is None:
            self.winId()
            handle = self.windowHandle()
        return handle

    def _start_system_move(self) -> bool:
        """Ask the compositor/window manager to move this frameless window."""
        handle = self._window_handle()
        if handle is None or not hasattr(handle, "startSystemMove"):
            return False
        try:
            return bool(handle.startSystemMove())
        except Exception:
            return False

    def _start_system_resize(self, region: str) -> bool:
        """Ask the compositor/window manager to resize this frameless window."""
        edges = self._SYSTEM_RESIZE_EDGES.get(region)
        if edges is None:
            return False
        handle = self._window_handle()
        if handle is None or not hasattr(handle, "startSystemResize"):
            return False
        try:
            return bool(handle.startSystemResize(edges))
        except Exception:
            return False

    def mousePressEvent(self, event):
        """Handle the mousepress event."""
        if event.button() == Qt.MouseButton.LeftButton:
            region = self._hit_region(event.position().toPoint())
            if region == 'drag':
                if self._start_system_move():
                    self._drag_pos = None
                    self._resize_dir = None
                    event.accept()
                    return
                self._drag_pos   = event.globalPosition().toPoint()
                self._resize_dir = None
            elif region:
                if self._start_system_resize(region):
                    self._drag_pos = None
                    self._resize_dir = None
                    event.accept()
                    return
                self._drag_pos         = event.globalPosition().toPoint()
                self._resize_dir       = region
                self._resize_start_geo = self.geometry()
            else:
                self._drag_pos   = None
                self._resize_dir = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle the mousemove event."""
        gpos = event.globalPosition().toPoint()
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            region = self._hit_region(event.position().toPoint())
            cur = self._CURSORS.get(region, Qt.CursorShape.ArrowCursor)
            self.setCursor(cur)
            return

        if self._drag_pos is None:
            return

        if self._resize_dir is None:
            delta = gpos - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = gpos
        else:
            dx  = gpos.x() - self._drag_pos.x()
            dy  = gpos.y() - self._drag_pos.y()
            geo = self._resize_start_geo
            d   = self._resize_dir
            x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()
            max_w = self.maximumWidth() if self.maximumWidth() > 0 else 16777215
            max_h = self.maximumHeight() if self.maximumHeight() > 0 else 16777215

            if 'r' in d:
                w = min(max_w, max(min_w, geo.width() + dx))
            if 'b' in d:
                h = min(max_h, max(min_h, geo.height() + dy))
            if 'l' in d:
                new_w = min(max_w, max(min_w, geo.width() - dx))
                x = geo.x() + (geo.width() - new_w)
                w = new_w
            if 't' in d:
                new_h = min(max_h, max(min_h, geo.height() - dy))
                y     = geo.y() + (geo.height() - new_h)
                h     = new_h

            self.setGeometry(x, y, w, h)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle the mouserelease event."""
        self._drag_pos   = None
        self._resize_dir = None
        super().mouseReleaseEvent(event)


    def resizeEvent(self, event):
        """Handle the resize event."""
        super().resizeEvent(event)
        if self._theme_fade_overlay is not None:
            self._theme_fade_overlay.setGeometry(self.rect())
        if hasattr(self, 'toast'):
            self._update_toast_anchor()
        self._save_geometry()

    def showEvent(self, event):
        """Handle the show event."""
        super().showEvent(event)
        handle = self.windowHandle()
        if handle is not None and not self._screen_hooked:
            handle.screenChanged.connect(
                lambda _screen: self._apply_wm_size_hints()
            )
            self._screen_hooked = True
        self._apply_wm_size_hints()

    def _apply_wm_size_hints(self):
        """Apply wm size hints."""
        max_w  = MAX_WINDOW_W
        max_h  = 1200
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo   = screen.availableGeometry()
            max_w = min(MAX_WINDOW_W, max(MIN_WINDOW_W, geo.width() - 48))
            max_h = max(MIN_WINDOW_H, int(geo.height() * 0.92))
        self.setMinimumSize(MIN_WINDOW_W, MIN_WINDOW_H)
        self.setMaximumSize(max_w, max_h)
        self._clamp_geometry_to_screen()

    def _show_shortcuts_panel(self):
        """Show shortcuts panel."""
        if hasattr(self, '_shortcuts_panel') and self._shortcuts_panel.isVisible():
            self._shortcuts_panel.close()
            return
        from .shortcuts_panel import ShortcutsPanel
        panel = ShortcutsPanel(ThemeManager.tokens(), parent=self)
        ThemeManager.subscribe(panel.apply_theme)
        panel.closed.connect(lambda: ThemeManager.unsubscribe(panel.apply_theme))
        panel.adjustSize()
        px = (self.width()  - panel.width())  // 2
        py = (self.height() - panel.height()) // 2
        from PyQt6.QtCore import QPoint as _QP
        panel.move(self.mapToGlobal(self.rect().topLeft()) + _QP(px, py))
        panel.show()
        self._shortcuts_panel = panel

    def _restore_geometry(self):
        """Handle restore geometry."""
        s = QSettings("Quacky", "Window")
        pos = s.value("pos", None)
        size = s.value("size", None)

        if size is not None and hasattr(size, "width") and hasattr(size, "height"):
            try:
                w = int(size.width())
                h = int(size.height())
                w = max(self.minimumWidth(), min(w, self.maximumWidth()))
                h = max(self.minimumHeight(), min(h, self.maximumHeight()))
                self.resize(w, h)
            except Exception:
                pass

        if pos is not None and hasattr(pos, "x") and hasattr(pos, "y"):
            try:
                self.move(pos)
            except Exception:
                pass

        self._clamp_geometry_to_screen()

    def _clamp_geometry_to_screen(self):
        """Keep current geometry fully visible on the active screen."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        geo = self.geometry()

        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        max_w = self.maximumWidth() if self.maximumWidth() > 0 else available.width()
        max_h = self.maximumHeight() if self.maximumHeight() > 0 else available.height()
        max_w = min(max_w, available.width())
        max_h = min(max_h, available.height())

        w = min(max(geo.width(), min_w), max_w)
        h = min(max(geo.height(), min_h), max_h)

        min_x = available.left()
        min_y = available.top()
        max_x = available.right() - w + 1
        max_y = available.bottom() - h + 1
        x = min(max(geo.x(), min_x), max_x)
        y = min(max(geo.y(), min_y), max_y)

        if (x, y, w, h) != (geo.x(), geo.y(), geo.width(), geo.height()):
            self.setGeometry(x, y, w, h)

    def _save_geometry(self):
        """Save geometry."""
        s = QSettings("Quacky", "Window")
        s.setValue("pos",  self.pos())
        s.setValue("size", self.size())

    def moveEvent(self, event):
        """Handle the move event."""
        super().moveEvent(event)
        self._save_geometry()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self._on_theme_changed)
        except Exception:
            pass
