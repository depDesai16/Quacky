"""
quacky_window.py — QuackyWindow

Drop-in replacement for quacky_gui.QuackyGUI.

BACKEND INTEGRATION — PRESERVED EXACTLY:
  ChatWorker       — unchanged (STT path)
  STTBridge        — unchanged
  send_message()   — unchanged
  _dispatch_text_message() — uses StreamingChatWorker
  _start_stt() / _stop_stt() — unchanged
  on_mic_toggle()  — unchanged
  _on_stt_command() / _on_stt_response() — unchanged
  _on_error()      — unchanged (+ cleans up stream)
  set_model_visible() / set_speechtospeech_enabled() — unchanged
  shutdown()       — unchanged

NEW (non-breaking):
  StreamingChatWorker — tries client.stream_message(); falls back to send_message()
  _on_chunk()         — routes chunk to timeline.append_stream_chunk()
  _on_stream_complete() — calls timeline.finalize_stream()
  Ctrl+T              — toggle Light/Dark theme
  Ctrl+L              — focus composer
  Escape              — clear input or hide
"""

import os
import sys

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR     = os.path.dirname(FRONTEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtCore    import (Qt, QThread, pyqtSignal, QObject,
                              QPropertyAnimation, QEasingCurve, QEvent, QTimer)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel,
                              QGraphicsOpacityEffect)
from PyQt6.QtGui     import QKeyEvent, QCursor
from PyQt6.QtCore    import QSettings, QPoint, QSignalBlocker

from theme          import ThemeManager
from draw_icon      import draw_icon
from quacky_model   import ModelWindow
from backend.client import QuackyClient

from widgets.card_widget   import CardWidget
from widgets.header_bar    import HeaderBar
from widgets.chat_timeline import ChatTimeline
from widgets.composer      import Composer
from widgets.icon_buttons  import MicButton, SendButton
from widgets.toast         import Toast

MAX_WINDOW_W = 1040
MIN_WINDOW_W = 600
MIN_WINDOW_H = 660



class ChatWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, client: QuackyClient, chat_id: str, message: str):
        super().__init__()
        self._client  = client
        self._chat_id = chat_id
        self._message = message

    def run(self):
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
        super().__init__()
        self._client  = client
        self._chat_id = chat_id
        self._message = message

    def run(self):
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
        super().__init__()
        self._client  = client
        self._chat_id = chat_id

    def handle_command(self, command: str) -> str:
        self.command_received.emit(command)
        result = self._client.send_message(self._chat_id, command, tts=False)
        if "error" in result:
            self.error_occurred.emit(result["error"])
            return f"[Error] {result['error']}"
        text = result.get("text", "")
        self.response_ready.emit(text)
        return text



class QuackyWindow(QWidget):
    """Frameless, always-on-top, draggable chat window."""

    def __init__(self, client: QuackyClient, chat_id: str):
        super().__init__()

        self._client                = client
        self._chat_id               = chat_id
        self._active_worker         = None
        self._stt                   = None
        self._stt_bridge: STTBridge | None = None
        self._stt_capture_enabled   = False
        self.speechtospeech_enabled = False
        self._drag_pos:        QPoint | None = None
        self._resize_dir:       str    | None = None
        self._resize_start_geo         = None
        self._last_failed_text: str    | None = None
        
        # User profile
        self.current_user = "Guest"
        
        # Initialize face recognition manager early (before camera)
        from face_recognition import FaceRecognitionManager
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
        self._apply_wm_size_hints()
        self.resize(620, 740)

        ThemeManager.load()
        self._restore_geometry()

        self.model_window = None
        try:
            self.model_window = ModelWindow()
            # Position relative to available screen geometry rather than
            # hardcoded pixel coordinates that break on different resolutions.
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
            # Keep chat UI usable even if OpenGL/model window isn't available.
            self.model_window = None

        self._theme_fade_overlay = None
        self._theme_fade_anim = None

        self._build_ui()
        self._install_resize_cursor_tracking()
        ThemeManager.subscribe(self._on_theme_changed)


    def _build_ui(self):
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
        self.header.user_chip_clicked.connect(self._show_user_menu)
        cl.addWidget(self.header)
        
        # Add tab bar
        self.tab_bar = self._create_tab_bar()
        cl.addWidget(self.tab_bar)
        
        # Create stacked widget to hold chat and camera views
        from PyQt6.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        
        # Chat view (existing timeline)
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        
        self.timeline = ChatTimeline(draw_icon_fn=draw_icon, parent=self.card)
        self._wire_suggestions()
        chat_layout.addWidget(self.timeline, 1)
        
        # Camera view
        from camera_view import CameraView
        self.camera_view = CameraView(parent=self.card)
        
        # Connect camera user recognition to profile switching
        self.camera_view.user_recognized.connect(self._on_user_profile_changed)
        
        # Add views to stacked widget
        self.stacked_widget.addWidget(self.chat_container)  # index 0
        self.stacked_widget.addWidget(self.camera_view)     # index 1
        
        cl.addWidget(self.stacked_widget, 1)

        self.mic_btn  = MicButton()
        self.send_btn = SendButton()
        self.composer = Composer(
            mic_button=self.mic_btn,
            send_button=self.send_btn,
            parent=self.card,
        )
        self.composer.input_field.send_requested.connect(self.send_message)
        self.send_btn.clicked.connect(self.send_message)
        self.composer.shortcuts_btn.clicked.connect(self._show_shortcuts_panel)
        self.composer.input_field.textChanged.connect(self._update_send_btn)
        self.composer.input_field.textChanged.connect(self._update_toast_anchor)
        self.mic_btn.toggled.connect(self.on_mic_toggle)
        cl.addWidget(self.composer)



        root.addWidget(self.card)
        self.toast = Toast(self.card)
        self._update_toast_anchor()
    
    def _create_tab_bar(self):
        """Create tab bar for switching between chat and camera"""
        from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
        
        tab_bar = QWidget()
        tab_bar.setFixedHeight(44)
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(16, 8, 16, 0)
        tab_layout.setSpacing(8)
        
        # Chat tab button
        self.chat_tab_btn = QPushButton("💬 Chat")
        self.chat_tab_btn.setCheckable(True)
        self.chat_tab_btn.setChecked(True)
        self.chat_tab_btn.clicked.connect(lambda: self._switch_tab(0))
        
        # Camera tab button
        self.camera_tab_btn = QPushButton("📷 Camera")
        self.camera_tab_btn.setCheckable(True)
        self.camera_tab_btn.clicked.connect(lambda: self._switch_tab(1))
        
        # Style tabs
        self._style_tab_buttons()
        
        tab_layout.addWidget(self.chat_tab_btn)
        tab_layout.addWidget(self.camera_tab_btn)
        tab_layout.addStretch()
        
        return tab_bar
    
    def _style_tab_buttons(self):
        """Apply theme styling to tab buttons"""
        t = ThemeManager.tokens()
        
        tab_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                color: {t['text.secondary']};
                font-size: 14px;
                font-weight: 500;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                color: {t['text.primary']};
                background: {t['bg.elevated']};
            }}
            QPushButton:checked {{
                color: {t['accent.primary']};
                border-bottom: 2px solid {t['accent.primary']};
            }}
        """
        
        self.chat_tab_btn.setStyleSheet(tab_style)
        self.camera_tab_btn.setStyleSheet(tab_style)
    
    def _switch_tab(self, index):
        """Switch between chat and camera tabs"""
        self.stacked_widget.setCurrentIndex(index)
        
        # Update tab button states
        self.chat_tab_btn.setChecked(index == 0)
        self.camera_tab_btn.setChecked(index == 1)
        
        # Hide composer when on camera tab
        if index == 1:
            self.composer.hide()
        else:
            self.composer.show()
    
    def _on_user_profile_changed(self, name, confidence):
        """Handle user profile change from face recognition"""
        if name != "Unknown" and name != self.current_user:
            self.current_user = name
            # Update header to show current user
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
        chip_pos = self.header.user_chip.mapToGlobal(self.header.user_chip.rect().bottomLeft())
        menu.exec(chip_pos)
    
    def _switch_to_user(self, user_name):
        """Manually switch to a user"""
        if user_name != self.current_user:
            self.current_user = user_name
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
        
        # Switch to camera tab
        self._switch_tab(1)
        
        # Show instructions
        QMessageBox.information(
            self,
            "Register New Face",
            "To register your face:\n\n"
            "1. Make sure your face is visible in the camera\n"
            "2. Enter your name in the text field at the bottom\n"
            "3. Click the '📸 Register Face' button\n\n"
            "The camera will recognize you automatically next time!"
        )
    
    def _start_face_id_switch(self):
        """Start Face ID authentication to switch profiles"""
        from face_id_dialog import FaceIDDialog
        
        # Stop camera tab if it's running
        was_on_camera = self.stacked_widget.currentIndex() == 1
        if hasattr(self, 'camera_view') and self.camera_view.camera_thread:
            self.camera_view.stop_camera()
            # Give camera time to fully release
            QTimer.singleShot(200, lambda: self._show_face_id_dialog(was_on_camera))
        else:
            self._show_face_id_dialog(was_on_camera)
    
    def _show_face_id_dialog(self, was_on_camera):
        """Show the Face ID dialog after camera is released"""
        from face_id_dialog import FaceIDDialog
        
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
            self.header.set_user(name)
            self.setWindowTitle(f"Quacky - {name}")
            self.timeline.add_system_message(
                f'<span style="color:#00d4ff;">✓ Authenticated as {name} '
                f'({confidence*100:.0f}% confidence)</span>'
            )

    def _wire_suggestions(self):
        if self.timeline._empty_widget:
            self.timeline._empty_widget.suggestion_clicked.connect(
                self._on_suggestion
            )

    def _on_suggestion(self, text: str):
        self.composer.input_field.setPlainText(text)
        self.composer.input_field.setFocus()


    def set_model_visible(self, visible: bool):
        if self.model_window is None:
            return
        self.model_window.show() if visible else self.model_window.hide()

    def set_speechtospeech_enabled(self, enabled: bool):
        self.speechtospeech_enabled = enabled

    def shutdown(self):
        self._stop_stt(full_shutdown=True)


    def send_message(self):
        text = self.composer.text().strip()
        if not text:
            return
        self.composer.clear()
        self._dispatch_text_message(text)

    def _dispatch_text_message(self, text: str):
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
        if listening == self._stt_capture_enabled and self._stt is not None:
            return
        if listening:
            self.mic_btn.setToolTip("Listening… (click to stop)")
            self._start_stt()
        else:
            self.mic_btn.setToolTip("Click to start voice input")
            self._stop_stt()

    def _start_stt(self):
        try:
            from backend.interact.speechToText.quacky_stt import QuackySpeechToText
        except ImportError:
            self._append_system("⚠ quacky_stt not found — voice input unavailable.")
            self._set_mic_checked(False)
            return

        if self._stt is None:
            try:
                self._stt = QuackySpeechToText(require_wake_word=False)
            except Exception as exc:
                self._append_system(f"⚠ Microphone init failed: {exc}")
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
            self._append_system(f"⚠ Voice input start failed: {exc}")
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
        if not self._stt:
            self._stt_capture_enabled = False
            return

        was_enabled = self._stt_capture_enabled

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
            self._append_system(f"⚠ Voice input stop fallback: {exc}")
            try:
                if self._stt and self._stt.is_listening:
                    self._stt.shutdown()
            except Exception:
                pass
        finally:
            self._stt_capture_enabled = False


    def _set_mic_checked(self, checked: bool):
        blocker = QSignalBlocker(self.mic_btn)
        self.mic_btn.setChecked(checked)
        del blocker


    def _on_chunk(self, chunk: str):
        self.timeline.append_stream_chunk(chunk)

    def _on_stream_complete(self, full_text: str):
        self.timeline.finalize_stream()
        self.header.set_status("responding")
        self._last_failed_text = None

    def _on_stt_command(self, command: str):
        self._append_user(command)
        self._set_input_busy(True)

    def _on_stt_response(self, text: str):
        self._append_quacky(text)
        self._set_input_busy(False)

    def _on_error(self, error: str):
        self.timeline.finalize_stream()
        self.timeline.hide_thinking()
        self._append_system(f"⚠ {error}")
        self._set_input_busy(False)
        if self._last_failed_text:
            self.timeline.show_retry_prompt(self._last_failed_text, self._on_retry)

    def _on_retry(self, text: str):
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
        self.timeline.add_user_message(text)
        self._install_resize_cursor_tracking()
        self._wire_suggestions()

    def _append_quacky(self, text: str):
        self.timeline.hide_thinking()
        self.timeline.add_assistant_message(text)
        self._install_resize_cursor_tracking()

    def _append_system(self, html: str):
        self.timeline.add_system_message(html)
        self._install_resize_cursor_tracking()

    def _set_input_busy(self, busy: bool):
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
        self.send_btn.setEnabled(
            bool(self.composer.input_field.toPlainText().strip())
        )
        self._update_toast_anchor()
        QTimer.singleShot(0, self._update_toast_anchor)

    def _update_toast_anchor(self):
        if not hasattr(self, 'toast'):
            return
        clearance = self.composer.height() + 8
        self.toast.set_bottom_clearance(clearance)
        timeline_clearance = max(28, int(self.composer.height() * 0.45))
        self.timeline.set_bottom_clearance(timeline_clearance)
        pill_clearance = clearance + 46
        self.timeline.set_new_message_pill_clearance(pill_clearance)


    def _on_theme_changed(self, tokens: dict):
        pass                                                             

    def _install_resize_cursor_tracking(self):
        self.setMouseTracking(True)
        self.installEventFilter(self)
        for w in self.findChildren(QWidget):
            w.setMouseTracking(True)
            w.installEventFilter(self)

    def _update_resize_cursor(self):
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
        if isinstance(obj, QWidget) and (obj is self or self.isAncestorOf(obj)):
            et = event.type()
            if et in (
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

    EDGE = 8
    CORNER_GRAB = 24

    def _hit_region(self, pos):
        """Return resize direction or 'drag' or None based on cursor position."""
        x, y  = pos.x(), pos.y()
        w, h  = self.width(), self.height()
        e     = self.EDGE
        c     = self.CORNER_GRAB

        if x <= c and y <= c:
            return 'tl'
        if x >= w - c and y <= c:
            return 'tr'
        if x <= c and y >= h - c:
            return 'bl'
        if x >= w - c and y >= h - c:
            return 'br'

        left  = x <= e
        right = x >= w - e
        top   = y <= e
        bot   = y >= h - e
        if top:              return 't'
        if bot:              return 'b'
        if left:             return 'l'
        if right:            return 'r'
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            region = self._hit_region(event.position().toPoint())
            if region == 'drag':
                self._drag_pos  = event.globalPosition().toPoint()
                self._resize_dir = None
            elif region:
                self._drag_pos   = event.globalPosition().toPoint()
                self._resize_dir = region
                self._resize_start_geo = self.geometry()
            else:
                self._drag_pos  = None
                self._resize_dir = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
            dx = gpos.x() - self._drag_pos.x()
            dy = gpos.y() - self._drag_pos.y()
            geo = self._resize_start_geo
            d   = self._resize_dir
            x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()

            if 'r' in d: w = max(min_w, geo.width()  + dx)
            if 'b' in d: h = max(min_h, geo.height() + dy)
            if 'l' in d:
                w = max(min_w, geo.width() - dx)
            if 't' in d:
                new_h = max(min_h, geo.height() - dy)
                y = geo.y() + (geo.height() - new_h)
                h = new_h

            self.setGeometry(x, y, w, h)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos   = None
        self._resize_dir = None
        super().mouseReleaseEvent(event)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._theme_fade_overlay is not None:
            self._theme_fade_overlay.setGeometry(self.rect())
        if hasattr(self, 'toast'):
            self._update_toast_anchor()
        self._save_geometry()

    def showEvent(self, event):
        super().showEvent(event)
        handle = self.windowHandle()
        if handle is not None and not self._screen_hooked:
            handle.screenChanged.connect(lambda _screen: self._apply_wm_size_hints())
            self._screen_hooked = True
        self._apply_wm_size_hints()

    def _apply_wm_size_hints(self):
        max_w = MAX_WINDOW_W
        max_h = 1200
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            max_w = min(MAX_WINDOW_W, max(MIN_WINDOW_W, geo.width() - 48))
            max_h = max(MIN_WINDOW_H, int(geo.height() * 0.92))
        self.setMinimumSize(MIN_WINDOW_W, MIN_WINDOW_H)
        self.setMaximumSize(max_w, max_h)

    def _show_shortcuts_panel(self):
        if hasattr(self, '_shortcuts_panel') and self._shortcuts_panel.isVisible():
            self._shortcuts_panel.close()
            return
        from shortcuts_panel import ShortcutsPanel
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
        s = QSettings("Quacky", "Window")
        pos  = s.value("pos",  None)
        size = s.value("size", None)
        if pos  is not None: self.move(pos)
        if size is not None: self.resize(size)

    def _save_geometry(self):
        s = QSettings("Quacky", "Window")
        s.setValue("pos",  self.pos())
        s.setValue("size", self.size())

    def moveEvent(self, event):
        super().moveEvent(event)
        self._save_geometry()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self._on_theme_changed)
        except Exception:
            pass
