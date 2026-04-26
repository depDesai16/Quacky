import logging

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget
from theme import ThemeManager

LOGGER = logging.getLogger(__name__)

class ToggleSlider(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._knob_x = 26.0 if checked else 4.0
        self._tokens = ThemeManager.tokens()

        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        ThemeManager.subscribe(self._on_theme)

    def _on_theme(self, tokens: dict):
        """Handle theme callbacks."""
        self._tokens = tokens
        self.update()

    def get_knob_x(self) -> float:
        """Return knob x."""
        return self._knob_x

    def set_knob_x(self, val: float):
        """Set knob x."""
        self._knob_x = val
        self.update()

    knob_x = pyqtProperty(float, get_knob_x, set_knob_x)

    def isChecked(self) -> bool:
        """Handle ischecked."""
        return self._checked

    def setChecked(self, val: bool):
        """Handle setchecked."""
        if val != self._checked:
            self._checked = val
            self._animate_to(26.0 if val else 4.0)

    def _animate_to(self, target: float):
        """Handle animate to."""
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        """Handle the mousepress event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate_to(26.0 if self._checked else 4.0)
            self.toggled.emit(self._checked)

    def paintEvent(self, _event):
        """Handle the paint event."""
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        radius = h / 2.0
        pen_w = 1.5
        inset = pen_w / 2.0

        if self._checked:
            track = QColor(t["accent.primary"])
            track.setAlphaF(0.85)
        else:
            track = QColor(t["bg.elevated"])

        p.setBrush(QBrush(track))
        p.setPen(QPen(QColor(t["border.strong"]), pen_w))
        p.drawRoundedRect(
            QRectF(inset, inset, w - pen_w, h - pen_w),
            radius - inset,
            radius - inset,
        )

        knob_size = h - 6.0
        p.setBrush(QBrush(QColor(t["text.primary"])))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(self._knob_x, 3.0, knob_size, knob_size))
        p.end()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception as exc:
            LOGGER.debug("Failed to unsubscribe toggle theme callback: %s", exc, exc_info=True)
