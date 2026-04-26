import logging
import math

from PyQt6.QtCore import (
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
    QRectF,
    QPointF,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QFont, QFontMetrics, QPen, QPainterPath,
)
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy

from theme import ThemeManager, FONT_STACK, FONT_FAMILY_UI

LOGGER = logging.getLogger(__name__)


def _safe_theme_unsubscribe(callback) -> None:
    try:
        ThemeManager.unsubscribe(callback)
    except Exception as exc:
        LOGGER.debug("Failed to unsubscribe theme callback: %s", exc, exc_info=True)


class StatusChip(QWidget):

    STATES = {
        "idle": "Idle",
        "thinking": "Thinking",
        "responding": "Responding",
        "error": "Error",
    }
    _MIN_H = 22
    _DOT_MIN = 7

    def __init__(self, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._state = "idle"
        self._tokens = ThemeManager.tokens()
        self._dot_alpha = 1.0
        self._dot_size = self._DOT_MIN

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_geometry()

        self._pulse_anim = QPropertyAnimation(self, b"dot_alpha", self)
        self._pulse_anim.setDuration(1100)
        self._pulse_anim.setStartValue(1.0)
        self._pulse_anim.setEndValue(0.28)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._pulse_anim.setLoopCount(-1)

        ThemeManager.subscribe(self.apply_theme)

    def _get_dot_alpha(self) -> float:
        """Return dot alpha."""
        return self._dot_alpha

    def _set_dot_alpha(self, v: float):
        """Set dot alpha."""
        self._dot_alpha = v
        self.update()

    dot_alpha = pyqtProperty(float, _get_dot_alpha, _set_dot_alpha)

    def set_state(self, state: str):
        """Set state."""
        if state not in self.STATES:
            raise ValueError(f"Unsupported status state: {state!r}")
        self._state = state
        if state == "thinking":
            self._pulse_anim.start()
        else:
            self._pulse_anim.stop()
            self._dot_alpha = 1.0
        self._update_geometry()
        self.update()

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self.update()

    def _dot_color(self) -> QColor:
        """Handle dot color."""
        key = f"status.{self._state}"
        c = QColor(self._tokens.get(key, self._tokens["status.idle"]))
        c.setAlphaF(self._dot_alpha)
        return c

    def _bg_color(self) -> QColor:
        """Handle bg color."""
        key = f"status.{self._state}"
        c = QColor(self._tokens.get(key, self._tokens["status.idle"]))
        c.setAlphaF(0.12)
        return c

    def _label(self) -> str:
        """Handle label."""
        return self.STATES.get(self._state, "Idle")

    def _status_font(self) -> QFont:
        """Handle status font."""
        base = QApplication.font()
        font = QFont(base.family() or FONT_FAMILY_UI)
        point_size = base.pointSizeF() if base.pointSizeF() > 0 else 10.0
        font.setPointSizeF(max(8.5, point_size - 0.2))
        font.setWeight(QFont.Weight.Medium)
        return font

    def _update_geometry(self):
        """Update chip dimensions from current font metrics."""
        fm = QFontMetrics(self._status_font())
        self.setFixedHeight(max(self._MIN_H, fm.height() + 8))
        self._dot_size = max(self._DOT_MIN, min(9, self.height() - 12))
        tw = fm.horizontalAdvance(self._label())
        self.setFixedWidth(tw + self._dot_size + 18)

    def paintEvent(self, event):
        """Handle the paint event."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        p.setBrush(QBrush(self._bg_color()))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        dot_x = 6.0
        dot_y = (h - self._dot_size) / 2
        p.setBrush(QBrush(self._dot_color()))
        p.drawEllipse(QRectF(dot_x, dot_y, self._dot_size, self._dot_size))
        p.setPen(QColor(self._tokens["text.secondary"]))
        font = self._status_font()
        p.setFont(font)
        text_x = int(dot_x + self._dot_size + 5)
        p.drawText(
            text_x, 0, w - text_x - 6, h,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label(),
        )
        p.end()

    def showEvent(self, event):
        """Handle the show event."""
        super().showEvent(event)
        self._update_geometry()

    def __del__(self):
        """Release resources during object cleanup."""
        _safe_theme_unsubscribe(self.apply_theme)


class WindowControlButton(QPushButton):

    def __init__(self, kind: str, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        if kind not in ("minimize", "close", "settings", "back"):
            raise ValueError(f"Unsupported window control kind: {kind!r}")
        self._kind = kind
        self._tokens = ThemeManager.tokens()
        self._hovered = False

        self.setText("")
        self.setFixedSize(34, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self.update()

    def enterEvent(self, event):
        """Handle the enter event."""
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle the leave event."""
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def _hover_bg(self) -> QColor:
        """Handle hover bg."""
        if self._kind == "close":
            return QColor(224, 85, 85, int(0.20 * 255))
        c = QColor(self._tokens["accent.primary"])
        c.setAlphaF(0.12)
        return c

    def _icon_color(self) -> QColor:
        """Handle icon color."""
        if self._hovered:
            if self._kind == "close":
                return QColor("#E05555")
            return QColor(self._tokens["accent.primary"])
        return QColor(self._tokens["text.muted"])

    def paintEvent(self, _event):
        """Handle the paint event."""
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

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        if self._kind == "minimize":
            pen = QPen(self._icon_color(), 2.2,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            half_len = 7.8
            y = cy + 1.0
            p.drawLine(int(cx - half_len), int(y), int(cx + half_len), int(y))

        elif self._kind == "close":
            pen = QPen(self._icon_color(), 1.9,
                       Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                       Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            arm = 4.7
            p.drawLine(int(cx - arm), int(cy - arm), int(cx + arm), int(cy + arm))
            p.drawLine(int(cx - arm), int(cy + arm), int(cx + arm), int(cy - arm))

        elif self._kind == "settings":
            self._draw_gear(p, cx, cy)

        elif self._kind == "back":
            self._draw_back_chevron(p, cx, cy)

        p.end()

    def _draw_gear(self, p: QPainter, cx: float, cy: float):
        """Handle draw gear."""
        pen = QPen(self._icon_color(), 1.5,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        teeth      = 8
        r_outer    = 7.2
        r_inner    = 5.2
        r_hole     = 2.4
        tooth_half = math.pi / teeth * 0.42

        path  = QPainterPath()
        first = True

        for i in range(teeth):
            base_angle = 2.0 * math.pi * i / teeth
            corners = [
                (base_angle - tooth_half, r_inner),
                (base_angle - tooth_half, r_outer),
                (base_angle + tooth_half, r_outer),
                (base_angle + tooth_half, r_inner),
            ]
            for angle, radius in corners:
                pt = QPointF(
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle),
                )
                if first:
                    path.moveTo(pt)
                    first = False
                else:
                    path.lineTo(pt)

            next_angle = 2.0 * math.pi * (i + 1) / teeth - tooth_half
            path.lineTo(QPointF(
                cx + r_inner * math.cos(next_angle),
                cy + r_inner * math.sin(next_angle),
            ))

        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QRectF(cx - r_hole, cy - r_hole, r_hole * 2, r_hole * 2))

    def _draw_back_chevron(self, p: QPainter, cx: float, cy: float):
        """Handle draw back chevron."""
        pen = QPen(self._icon_color(), 2.0,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        arm   = 5.0
        tip_x = cx - 2.0   # slight left bias
        p.drawLine(
            QPointF(tip_x + arm * 0.72, cy - arm),
            QPointF(tip_x,              cy),
        )
        p.drawLine(
            QPointF(tip_x,              cy),
            QPointF(tip_x + arm * 0.72, cy + arm),
        )


class HeaderBar(QWidget):

    settings_clicked = pyqtSignal()
    back_clicked     = pyqtSignal()
    minimize_clicked = pyqtSignal()
    close_clicked    = pyqtSignal()

    HEIGHT = 54

    def __init__(self, icon, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setFixedHeight(self.HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._tokens = ThemeManager.tokens()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(8)

        self._back_btn = WindowControlButton(kind="back")
        self._back_btn.setToolTip("Back to chat")
        self._back_btn.clicked.connect(self.back_clicked)
        self._back_btn.hide()
        layout.addWidget(self._back_btn)

        self._avatar = QLabel()
        self._avatar.setPixmap(icon.pixmap(40, 40))
        self._avatar.setFixedSize(40, 40)
        self._avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._avatar)

        self._title = QLabel("Quacky")
        self._title.setObjectName("headerTitle")
        layout.addWidget(self._title)

        self.status_chip = StatusChip()
        layout.addWidget(self.status_chip)

        layout.addStretch()

        self._settings_btn = WindowControlButton(kind="settings")
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settings_clicked)
        layout.addWidget(self._settings_btn)

        self._min_btn = WindowControlButton(kind="minimize")
        self._min_btn.clicked.connect(self.minimize_clicked)
        layout.addWidget(self._min_btn)

        self._close_btn = WindowControlButton(kind="close")
        self._close_btn.clicked.connect(self.close_clicked)
        layout.addWidget(self._close_btn)

        self._apply_style()
        ThemeManager.subscribe(self.apply_theme)


    def enter_settings_mode(self):
        """Handle enter settings mode."""
        self._avatar.hide()
        self.status_chip.hide()
        self._settings_btn.hide()
        self._back_btn.show()
        self._title.setText("Settings")

    def exit_settings_mode(self):
        """Handle exit settings mode."""
        self._back_btn.hide()
        self._avatar.show()
        self.status_chip.show()
        self._settings_btn.show()
        self._title.setText("Quacky")


    def _apply_style(self):
        """Apply style."""
        t = self._tokens
        self.setStyleSheet(f"""
            QWidget#headerBar {{
                background: transparent;
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
        """)
        for btn in (self._back_btn, self._settings_btn,
                    self._min_btn, self._close_btn):
            btn.apply_theme(t)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self._apply_style()
        self.status_chip.apply_theme(tokens)

    def set_status(self, state: str):
        """Set status."""
        self.status_chip.set_state(state)

    def __del__(self):
        """Release resources during object cleanup."""
        _safe_theme_unsubscribe(self.apply_theme)
