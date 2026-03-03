"""
widgets/header_bar.py - HeaderBar + StatusChip

HeaderBar layout (left -> right):
  [avatar 28px] [title "Quacky"] [StatusChip] [stretch] [minimize] [close]

StatusChip states: idle | thinking | responding | error
  - Thinking dot pulses via QPropertyAnimation.
  - Color cross-fade on state change via QPropertyAnimation on a custom property.
"""

from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QRectF,
    pyqtSignal,
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QFont, QFontMetrics, QPen
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from theme import ThemeManager, FONT_STACK, FONT_FAMILY_UI


class StatusChip(QWidget):
    """Animated pill: colored dot + text label."""

    STATES = {
        "idle": "Idle",
        "thinking": "Thinking",
        "responding": "Responding",
        "error": "Error",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"
        self._tokens = ThemeManager.tokens()
        self._dot_alpha = 1.0

        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._pulse_anim = QPropertyAnimation(self, b"dot_alpha", self)
        self._pulse_anim.setDuration(1100)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setEndValue(0.28)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._pulse_anim.setLoopCount(-1)

        ThemeManager.subscribe(self.apply_theme)

    def _get_dot_alpha(self) -> float:
        return self._dot_alpha

    def _set_dot_alpha(self, v: float):
        self._dot_alpha = v
        self.update()

    dot_alpha = pyqtProperty(float, _get_dot_alpha, _set_dot_alpha)

    def set_state(self, state: str):
        assert state in self.STATES
        self._state = state

        if state == "thinking":
            self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._dot_alpha = 1.0

        self._update_width()
        self.update()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def _dot_color(self) -> QColor:
        key = f"status.{self._state}"
        c = QColor(self._tokens.get(key, self._tokens["status.idle"]))
        c.setAlphaF(self._dot_alpha)
        return c

    def _bg_color(self) -> QColor:
        key = f"status.{self._state}"
        c = QColor(self._tokens.get(key, self._tokens["status.idle"]))
        c.setAlphaF(0.12)
        return c

    def _label(self) -> str:
        return self.STATES.get(self._state, "Idle")

    def _status_font(self) -> QFont:
        font = QFont(FONT_FAMILY_UI)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        return font

    def _update_width(self):
        fm = QFontMetrics(self._status_font())
        tw = fm.horizontalAdvance(self._label())
        self.setFixedWidth(tw + 7 + 5 + 12 + 6)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = h / 2

        p.setBrush(QBrush(self._bg_color()))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        dot_x = 6.0
        dot_y = (h - 7) / 2
        p.setBrush(QBrush(self._dot_color()))
        p.drawEllipse(QRectF(dot_x, dot_y, 7, 7))

        p.setPen(QColor(self._tokens["text.secondary"]))
        font = self._status_font()
        p.setFont(font)
        text_x = int(dot_x + 7 + 5)
        p.drawText(
            text_x,
            0,
            w - text_x - 6,
            h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label(),
        )
        p.end()

    def showEvent(self, event):
        super().showEvent(event)
        self._update_width()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass


class WindowControlButton(QPushButton):
    """Custom-painted window control for consistent sizing across OS fonts."""

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        assert kind in ("minimize", "close")
        self._kind = kind
        self._tokens = ThemeManager.tokens()
        self._hovered = False

        self.setText("")
        self.setFixedSize(34, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def _hover_bg(self) -> QColor:
        if self._kind == "close":
            return QColor(224, 85, 85, int(0.20 * 255))
        c = QColor(self._tokens["accent.primary"])
        c.setAlphaF(0.12)
        return c

    def _icon_color(self) -> QColor:
        if self._hovered:
            if self._kind == "close":
                return QColor("#E05555")
            return QColor(self._tokens["accent.primary"])
        return QColor(self._tokens["text.muted"])

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isDown():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, int(0.18 * 255)))
            p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
        elif self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._hover_bg())
            p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)

        stroke = 2.2 if self._kind == "minimize" else 1.9
        pen = QPen(
            self._icon_color(),
            stroke,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        if self._kind == "minimize":
            half_len = 7.8
            y = cy + 1.0
            p.drawLine(int(cx - half_len), int(y), int(cx + half_len), int(y))
        else:
            arm = 4.7
            p.drawLine(int(cx - arm), int(cy - arm), int(cx + arm), int(cy + arm))
            p.drawLine(int(cx - arm), int(cy + arm), int(cx + arm), int(cy - arm))
        p.end()


class HeaderBar(QWidget):
    """
    Fixed-height header:
      [avatar] [title] [status chip]  ...  [minimize] [close]

    Signals:
      minimize_clicked - hide the window
      close_clicked    - quit the app
    """

    minimize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    HEIGHT = 54

    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setFixedHeight(self.HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._tokens = ThemeManager.tokens()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(8)

        avatar = QLabel()
        avatar.setPixmap(icon.pixmap(30, 30))
        avatar.setFixedSize(30, 30)
        avatar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(avatar)

        title = QLabel("Quacky")
        title.setObjectName("headerTitle")
        layout.addWidget(title)

        self.status_chip = StatusChip()
        layout.addWidget(self.status_chip)

        layout.addStretch()

        self._min_btn = self._make_control_btn(is_close=False)
        self._min_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(self._min_btn)

        self._close_btn = self._make_control_btn(is_close=True)
        self._close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self._close_btn)

        self._apply_style()
        ThemeManager.subscribe(self.apply_theme)

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(
            f"""
            QWidget#headerBar {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {t['border.strong']};
            }}
            QLabel#headerTitle {{
                font-family: {FONT_STACK};
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 0.2px;
                color: {t['text.primary']};
                background: transparent;
                border: none;
            }}
        """
        )
        self._min_btn.apply_theme(t)
        self._close_btn.apply_theme(t)

    def _make_control_btn(self, is_close: bool = False) -> WindowControlButton:
        kind = "close" if is_close else "minimize"
        return WindowControlButton(kind)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_style()
        self.status_chip.apply_theme(tokens)

    def set_status(self, state: str):
        self.status_chip.set_state(state)

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
