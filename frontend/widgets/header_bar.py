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


class UserProfileChip(QWidget):
    """User profile indicator chip showing current user (Guest or specific user)"""
    
    user_clicked = pyqtSignal()  # Signal when chip is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._user_name = "Guest"
        self._tokens = ThemeManager.tokens()
        
        self.setFixedHeight(22)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to switch user or register")
        
        ThemeManager.subscribe(self.apply_theme)
    
    def mousePressEvent(self, event):
        """Handle click to open user menu"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.user_clicked.emit()
        super().mousePressEvent(event)
    
    def set_user(self, name: str):
        """Set the current user name"""
        self._user_name = name if name and name != "Unknown" else "Guest"
        self._update_width()
        self.update()
    
    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()
    
    def _is_guest(self) -> bool:
        return self._user_name == "Guest"
    
    def _bg_color(self) -> QColor:
        if self._is_guest():
            # Gray for guest
            c = QColor(self._tokens["text.muted"])
            c.setAlphaF(0.12)
        else:
            # Accent color for recognized user
            c = QColor(self._tokens["accent.primary"])
            c.setAlphaF(0.15)
        return c
    
    def _icon_color(self) -> QColor:
        if self._is_guest():
            return QColor(self._tokens["text.muted"])
        else:
            return QColor(self._tokens["accent.primary"])
    
    def _text_color(self) -> QColor:
        if self._is_guest():
            return QColor(self._tokens["text.secondary"])
        else:
            return QColor(self._tokens["accent.primary"])
    
    def _profile_font(self) -> QFont:
        font = QFont(FONT_FAMILY_UI)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium if not self._is_guest() else QFont.Weight.Normal)
        return font
    
    def _update_width(self):
        fm = QFontMetrics(self._profile_font())
        tw = fm.horizontalAdvance(self._user_name)
        # icon(12) + spacing(5) + text + padding(12)
        self.setFixedWidth(12 + 5 + tw + 12)
    
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        r = h / 2
        
        # Background
        p.setBrush(QBrush(self._bg_color()))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        
        # User icon (simple circle with person symbol)
        icon_x = 6.0
        icon_y = (h - 12) / 2
        p.setPen(self._icon_color())
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.drawText(int(icon_x), int(icon_y), 12, 12,
                   Qt.AlignmentFlag.AlignCenter, "👤")
        
        # User name text
        p.setPen(self._text_color())
        font = self._profile_font()
        p.setFont(font)
        text_x = int(icon_x + 12 + 5)
        p.drawText(text_x, 0, w - text_x - 6, h,
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._user_name)
        p.end()
    
    def showEvent(self, event):
        super().showEvent(event)
        self._update_width()
    
    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass


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
      [avatar] [title] [status chip] [user chip]  ...  [minimize] [close]

    Signals:
      minimize_clicked - hide the window
      close_clicked    - quit the app
      user_chip_clicked - user wants to switch profile
    """

    minimize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    user_chip_clicked = pyqtSignal()

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
        
        # User profile chip
        self.user_chip = UserProfileChip()
        self.user_chip.user_clicked.connect(self._on_user_chip_clicked)
        layout.addWidget(self.user_chip)

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
        self.user_chip.apply_theme(tokens)

    def set_status(self, state: str):
        self.status_chip.set_state(state)
    
    def set_user(self, name: str):
        """Update the user profile chip"""
        self.user_chip.set_user(name)
    
    def _on_user_chip_clicked(self):
        """Forward user chip click signal"""
        self.user_chip_clicked.emit()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
