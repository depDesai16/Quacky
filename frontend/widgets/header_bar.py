
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
        assert state in self.STATES
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
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass


class WindowControlButton(QPushButton):

    def __init__(self, kind: str, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        assert kind in ("minimize", "close", "settings", "back")
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
    """
    Fixed-height header:
      [avatar] [title] [status chip] [user chip]  ...  [settings] [minimize] [close]

    Signals:
      settings_clicked - open settings
      back_clicked - return from settings
      minimize_clicked - hide the window
      close_clicked - quit the app
      user_chip_clicked - user wants to switch profile
    """

    settings_clicked = pyqtSignal()
    back_clicked     = pyqtSignal()
    minimize_clicked = pyqtSignal()
    close_clicked    = pyqtSignal()
    user_chip_clicked = pyqtSignal()

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
        self._avatar.setPixmap(icon.pixmap(30, 30))
        self._avatar.setFixedSize(30, 30)
        self._avatar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._avatar)

        self._title = QLabel("Quacky")
        self._title.setObjectName("headerTitle")
        layout.addWidget(self._title)

        self.status_chip = StatusChip()
        layout.addWidget(self.status_chip)
        
        # User profile chip
        self.user_chip = UserProfileChip()
        self.user_chip.user_clicked.connect(self._on_user_chip_clicked)
        layout.addWidget(self.user_chip)

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
        """)
        for btn in (self._back_btn, self._settings_btn,
                    self._min_btn, self._close_btn):
            btn.apply_theme(t)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self._apply_style()
        self.status_chip.apply_theme(tokens)
        self.user_chip.apply_theme(tokens)

    def set_status(self, state: str):
        """Set status."""
        self.status_chip.set_state(state)
    
    def set_user(self, name: str):
        """Update the user profile chip"""
        self.user_chip.set_user(name)
    
    def _on_user_chip_clicked(self):
        """Forward user chip click signal"""
        self.user_chip_clicked.emit()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
