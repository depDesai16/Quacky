"""
camera_view.py - Camera view widget with face tracking and analysis
"""
import cv2
from PyQt6.QtCore import (Qt, QThread, pyqtSignal, QRectF, QPointF,
                           QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer)
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QSizePolicy, QAbstractButton,
                              QFrame)
from PyQt6.QtGui import (QImage, QPixmap, QPainter, QColor, QPen,
                          QPainterPath, QBrush, QFont)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import ThemeManager, FONT_FAMILY_UI, FONT_STACK
from .camera_analyzer import CameraAnalyzer


# ─────────────────────────────────────────────
# Camera capture thread
# ─────────────────────────────────────────────

class CameraThread(QThread):
    """Thread for capturing and analyzing camera frames."""
    frame_ready = pyqtSignal(object, dict)

    def __init__(self):
        super().__init__()
        self.running  = False
        self.cap      = None
        self.analyzer = CameraAnalyzer()

    def run(self):
        self.cap     = cv2.VideoCapture(0)
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                results = self.analyzer.analyze_frame(frame)
                self.frame_ready.emit(frame, results)
            self.msleep(33)

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.analyzer.cleanup()


# ─────────────────────────────────────────────
# Status chip
# ─────────────────────────────────────────────

class _StatusChip(QWidget):
    """Pill-shaped status indicator with dot + label."""

    def __init__(self, icon_kind: str, text: str, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens    = tokens
        self._icon_kind = icon_kind
        self._text      = text
        self._active    = False
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_size()

    def set_text(self, text: str, active: bool = False):
        self._text   = text
        self._active = active
        self._update_size()
        self.update()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def _update_size(self):
        from PyQt6.QtGui import QFontMetrics
        f  = self._make_font()
        fm = QFontMetrics(f)
        tw = fm.horizontalAdvance(self._text)
        self.setFixedSize(tw + 36, 26)

    def _make_font(self) -> QFont:
        f = QFont(FONT_FAMILY_UI)
        f.setPointSizeF(10.5)
        f.setWeight(QFont.Weight.Medium)
        return f

    def paintEvent(self, _event):
        t   = self._tokens
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background pill
        accent = QColor(t["accent.primary"])
        if self._active:
            bg = QColor(t["accent.subtleBg"])
            dot_c = accent
        else:
            bg = QColor(t["bg.elevated"])
            dot_c = QColor(t["text.muted"])

        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        # Dot
        dot_r = 4.0
        dot_x = 10.0
        dot_y = h / 2.0
        p.setBrush(QBrush(dot_c))
        p.drawEllipse(QPointF(dot_x, dot_y), dot_r, dot_r)

        # Label
        text_color = QColor(t["accent.primary"] if self._active else t["text.secondary"])
        p.setPen(text_color)
        p.setFont(self._make_font())
        p.drawText(
            int(dot_x + dot_r + 6), 0,
            w - int(dot_x + dot_r + 10), h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )
        p.end()


# ─────────────────────────────────────────────
# Register button
# ─────────────────────────────────────────────

class _RegisterButton(QAbstractButton):
    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens  = tokens
        self._hovered = False
        self.setText("Register Face")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_width()

    def _update_width(self):
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font())
        self.setFixedWidth(fm.horizontalAdvance(self.text()) + 40)

    def _font(self) -> QFont:
        f = QFont(FONT_FAMILY_UI)
        f.setPointSizeF(11)
        f.setWeight(QFont.Weight.DemiBold)
        return f

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def enterEvent(self, e):
        self._hovered = True;  self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def paintEvent(self, _event):
        t  = self._tokens
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self.isDown():
            bg = QColor(t["accent.pressed"])
        elif self._hovered:
            bg = QColor(t["accent.hover"])
        else:
            bg = QColor(t["accent.primary"])

        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), 8, 8)

        p.setPen(QColor("#FFFFFF"))
        p.setFont(self._font())
        p.drawText(QRectF(0, 0, w, h),
                   Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


# ─────────────────────────────────────────────
# Back button (chevron left)
# ─────────────────────────────────────────────

class _BackButton(QAbstractButton):
    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens  = tokens
        self._hovered = False
        self.setFixedSize(80, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Back to chat")

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def enterEvent(self, e):
        self._hovered = True;  self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def paintEvent(self, _event):
        t  = self._tokens
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())

        # Pill background on hover
        if self._hovered or self.isDown():
            bg = QColor(t["bg.elevated"])
            p.setBrush(QBrush(bg))
            p.setPen(QPen(QColor(t["border.subtle"]), 1))
            p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        # Chevron
        ic = QColor(t["accent.primary"] if self._hovered else t["text.secondary"])
        pen = QPen(ic, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        arm = 4.5
        cx  = 14.0
        cy  = h / 2.0
        p.drawLine(QPointF(cx + arm * 0.7, cy - arm),
                   QPointF(cx,             cy))
        p.drawLine(QPointF(cx,             cy),
                   QPointF(cx + arm * 0.7, cy + arm))

        # "Back" label
        p.setPen(ic)
        f = QFont(FONT_FAMILY_UI)
        f.setPointSizeF(11)
        f.setWeight(QFont.Weight.Medium)
        p.setFont(f)
        p.drawText(QRectF(24, 0, w - 24, h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   "Back")
        p.end()


# ─────────────────────────────────────────────
# Face outline overlay widget
# ─────────────────────────────────────────────

class _FaceOverlay(QWidget):
    """Draws animated face-detection rectangles over the camera feed."""

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens  = tokens
        self._faces   = []
        self._attentive = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def update_faces(self, faces, attentive: bool, scale_x: float, scale_y: float,
                     offset_x: int, offset_y: int):
        self._faces     = faces
        self._attentive = attentive
        self._sx, self._sy   = scale_x, scale_y
        self._ox, self._oy   = offset_x, offset_y
        self.update()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def paintEvent(self, _event):
        if not self._faces:
            return
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        for (fx, fy, fw, fh) in self._faces:
            rx = self._ox + int(fx * self._sx)
            ry = self._oy + int(fy * self._sy)
            rw = int(fw * self._sx)
            rh = int(fh * self._sy)

            accent = QColor(t["accent.primary"] if self._attentive else t["state.warn"])
            accent.setAlphaF(0.85)
            pen = QPen(accent, 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

            # Corner bracket style instead of full rectangle
            cs = min(rw, rh) // 4  # corner segment length
            corners = [
                # top-left
                [(rx, ry + cs), (rx, ry), (rx + cs, ry)],
                # top-right
                [(rx + rw - cs, ry), (rx + rw, ry), (rx + rw, ry + cs)],
                # bottom-left
                [(rx, ry + rh - cs), (rx, ry + rh), (rx + cs, ry + rh)],
                # bottom-right
                [(rx + rw - cs, ry + rh), (rx + rw, ry + rh), (rx + rw, ry + rh - cs)],
            ]
            for pts in corners:
                path = QPainterPath()
                path.moveTo(QPointF(*pts[0]))
                path.lineTo(QPointF(*pts[1]))
                path.lineTo(QPointF(*pts[2]))
                p.drawPath(path)

        p.end()


# ─────────────────────────────────────────────
# Main CameraView
# ─────────────────────────────────────────────

class CameraView(QWidget):
    """Modern camera view widget fitting the Quacky aesthetic."""

    emotion_detected  = pyqtSignal(str, float)
    gesture_detected  = pyqtSignal(str)
    attention_changed = pyqtSignal(bool)
    user_recognized   = pyqtSignal(str, float)
    back_requested    = pyqtSignal()          # ← back to chat

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens       = ThemeManager.tokens()
        self.camera_thread = None
        self.current_frame = None
        self._scale_x      = 1.0
        self._scale_y      = 1.0
        self._off_x        = 0
        self._off_y        = 0

        self._build_ui()
        ThemeManager.subscribe(self._on_theme)

    # ── UI Construction ──────────────────────

    def _build_ui(self):
        t   = self._tokens
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(48)
        topbar.setObjectName("camTopBar")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(16, 0, 16, 0)
        tb.setSpacing(12)

        self._back_btn = _BackButton(t)
        self._back_btn.clicked.connect(self.back_requested)
        tb.addWidget(self._back_btn)

        # Title
        title = QLabel("Camera")
        title.setObjectName("camTitle")
        tb.addWidget(title)

        tb.addStretch()

        # Status chips (right side of topbar)
        self._chip_user      = _StatusChip("user",      "Guest",      t)
        self._chip_emotion   = _StatusChip("emotion",   "Neutral",    t)
        self._chip_attention = _StatusChip("attention", "Attentive",  t, )
        for chip in (self._chip_user, self._chip_emotion, self._chip_attention):
            tb.addWidget(chip)

        root.addWidget(topbar)

        # ── Divider ──────────────────────────
        div = QFrame()
        div.setFixedHeight(1)
        div.setObjectName("camDivider")
        root.addWidget(div)

        # ── Camera frame container ────────────
        self._cam_container = QWidget()
        self._cam_container.setObjectName("camContainer")
        cam_lay = QVBoxLayout(self._cam_container)
        cam_lay.setContentsMargins(20, 20, 20, 16)
        cam_lay.setSpacing(0)

        # Camera label (video feed)
        self._cam_label = QLabel()
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setObjectName("camFeed")
        self._cam_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        cam_lay.addWidget(self._cam_label, 1)

        # Face overlay (sits on top, same parent)
        self._overlay = _FaceOverlay(t, self._cam_label)
        self._overlay.setGeometry(self._cam_label.rect())

        root.addWidget(self._cam_container, 1)

        # ── Bottom bar (register) ─────────────
        self._bottom_bar = QWidget()
        self._bottom_bar.setObjectName("camBottomBar")
        bb = QHBoxLayout(self._bottom_bar)
        bb.setContentsMargins(20, 12, 20, 16)
        bb.setSpacing(10)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter name to register face…")
        self._name_input.setObjectName("camNameInput")
        self._name_input.setFixedHeight(36)
        self._name_input.setMaximumWidth(260)

        self._reg_btn = _RegisterButton(t)
        self._reg_btn.clicked.connect(self._on_register_user)

        bb.addWidget(self._name_input)
        bb.addWidget(self._reg_btn)
        bb.addStretch()

        # Registered-users hint
        self._hint_lbl = QLabel()
        self._hint_lbl.setObjectName("camHint")
        bb.addWidget(self._hint_lbl)

        root.addWidget(self._bottom_bar)

        self._apply_theme()

    # ── Theme ─────────────────────────────────

    def _on_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_theme()

    def _apply_theme(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QWidget#camTopBar {{
                background: {t['bg.surface']};
            }}
            QLabel#camTitle {{
                font-family: {FONT_STACK};
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.3px;
                color: {t['text.primary']};
                background: transparent;
            }}
            QFrame#camDivider {{
                background: {t['border.subtle']};
                border: none;
            }}
            QWidget#camContainer {{
                background: {t['bg.canvas']};
            }}
            QLabel#camFeed {{
                background: {t['bg.canvas']};
                border: 1px solid {t['border.subtle']};
                border-radius: 10px;
            }}
            QWidget#camBottomBar {{
                background: {t['bg.surface']};
                border-top: 1px solid {t['border.subtle']};
            }}
            QLineEdit#camNameInput {{
                background: {t['bg.elevated']};
                border: 1px solid {t['border.subtle']};
                border-radius: 8px;
                color: {t['text.primary']};
                font-family: {FONT_STACK};
                font-size: 13px;
                padding: 0px 12px;
            }}
            QLineEdit#camNameInput:focus {{
                border-color: {t['accent.primary']};
            }}
            QLabel#camHint {{
                color: {t['text.muted']};
                font-family: {FONT_STACK};
                font-size: 11px;
                background: transparent;
            }}
        """)
        for chip in (self._chip_user, self._chip_emotion, self._chip_attention):
            chip.apply_theme(t)
        self._back_btn.apply_theme(t)
        self._reg_btn.apply_theme(t)
        self._overlay.apply_theme(t)

    # ── Camera control ────────────────────────

    def start_camera(self):
        if self.camera_thread:
            return
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self._on_frame_ready)
        self.camera_thread.analyzer.emotion_detected.connect(self._on_emotion)
        self.camera_thread.analyzer.gesture_detected.connect(self._on_gesture)
        self.camera_thread.analyzer.attention_changed.connect(self._on_attention)
        self.camera_thread.start()

    def stop_camera(self):
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread.wait()
            self.camera_thread = None
            self._cam_label.clear()

    # ── Frame handling ────────────────────────

    def _on_frame_ready(self, frame, results):
        self.current_frame = frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w, ch  = rgb.shape
        qt_img    = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap    = QPixmap.fromImage(qt_img)

        label_w = self._cam_label.width()
        label_h = self._cam_label.height()
        scaled  = pixmap.scaled(
            label_w, label_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cam_label.setPixmap(scaled)

        # Compute scale factors for overlay alignment
        sw, sh = scaled.width(), scaled.height()
        self._scale_x = sw / w
        self._scale_y = sh / h
        self._off_x   = (label_w - sw) // 2
        self._off_y   = (label_h - sh) // 2

        self._overlay.setGeometry(self._cam_label.geometry()
                                   .adjusted(20, 20, -20, -16)
                                   if False else self._cam_label.rect())
        self._overlay.resize(self._cam_label.size())
        self._overlay.update_faces(
            results.get("faces", []),
            results.get("attention", True),
            self._scale_x, self._scale_y,
            self._off_x, self._off_y,
        )

    # ── Signal handlers ───────────────────────

    def _on_emotion(self, emotion: str, confidence: float):
        labels = {
            "happy":    "Happy",
            "neutral":  "Neutral",
            "surprised":"Surprised",
            "focused":  "Focused",
        }
        self._chip_emotion.set_text(labels.get(emotion, "Neutral"),
                                    active=(emotion == "happy"))
        self.emotion_detected.emit(emotion, confidence)

    def _on_gesture(self, gesture: str):
        self.gesture_detected.emit(gesture)

    def _on_attention(self, is_attentive: bool):
        self._chip_attention.set_text(
            "Attentive" if is_attentive else "Distracted",
            active=is_attentive,
        )
        self.attention_changed.emit(is_attentive)

    def _on_user_recognized(self, name: str, confidence: float):
        display = name if name != "Unknown" else "Guest"
        self._chip_user.set_text(display, active=(name != "Unknown"))
        self.user_recognized.emit(name, confidence)

    # ── Registration ──────────────────────────

    def _on_register_user(self):
        from PyQt6.QtWidgets import QMessageBox
        name = self._name_input.text().strip()
        if not name:
            return
        if not self.camera_thread or self.current_frame is None:
            return
        success, message = self.camera_thread.analyzer.register_user(
            name, self.current_frame
        )
        if success:
            self._name_input.clear()
            users = self.camera_thread.analyzer.get_registered_users()
            count = len(users)
            self._hint_lbl.setText(
                f"{count} registered user{'s' if count != 1 else ''}"
            )
        else:
            QMessageBox.warning(self, "Registration Failed", message)

    # ── Lifecycle ─────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_overlay") and hasattr(self, "_cam_label"):
            self._overlay.resize(self._cam_label.size())

    def showEvent(self, event):
        super().showEvent(event)
        self.start_camera()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.stop_camera()

    def __del__(self):
        try:
            self.stop_camera()
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass