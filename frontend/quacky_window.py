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
from PyQt6.QtCore    import QSettings, QPoint

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
        self.speechtospeech_enabled = False
        self._drag_pos:        QPoint | None = None
        self._resize_dir:       str    | None = None
        self._resize_start_geo         = None
        self._last_failed_text: str    | None = None

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
        cl.addWidget(self.header)

        self.timeline = ChatTimeline(draw_icon_fn=draw_icon, parent=self.card)
        self._wire_suggestions()
        cl.addWidget(self.timeline, 1)

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
        self._stop_stt()


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
            self.mic_btn.setChecked(False)
            return

        if self._stt is None:
            try:
                self._stt = QuackySpeechToText(require_wake_word=False)
            except Exception as exc:
                self._append_system(f"⚠ Microphone init failed: {exc}")
                self.mic_btn.setChecked(False)
                return

            self._stt_bridge = STTBridge(self._client, self._chat_id)
            self._stt_bridge.command_received.connect(self._on_stt_command)
            self._stt_bridge.response_ready.connect(self._on_stt_response)
            self._stt_bridge.error_occurred.connect(self._on_error)
            self._stt.set_callback(self._stt_bridge.handle_command)

        self._stt.start()
        self._append_system(
            "Voice input active - speak your command."
        )

    def _stop_stt(self):
        if self._stt and self._stt.is_listening:
            self._stt.shutdown()
            self._append_system("🔇 Voice input stopped.")


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
