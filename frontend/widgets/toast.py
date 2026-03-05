
from PyQt6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui     import QColor
from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect

from theme import ThemeManager, FONT_STACK

TOAST_DURATION_MS = 2500
FADE_IN_MS        = 200
FADE_OUT_MS       = 180
MARGIN_BOTTOM     = 16


class Toast(QLabel):

    def __init__(self, parent):
        """Initialize the instance state."""
        super().__init__(parent)
        self._tokens = ThemeManager.tokens()
        self._bottom_clearance = 0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(False)
        self.hide()
        self.raise_()

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self._fade_anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)
        ThemeManager.subscribe(self.apply_theme)

    def set_bottom_clearance(self, px: int):
        """Set bottom clearance."""
        self._bottom_clearance = max(0, int(px))
        self._reposition()

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens


    def show_message(self, text: str, kind: str = "success"):
        """Show message."""
        self._dismiss_timer.stop()
        self._fade_anim.stop()

        t  = self._tokens
        bg = t.get(f"state.{kind}Bg", t["state.successBg"])
        fg = t.get(f"state.{kind}",   t["state.success"])

        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                border: 1px solid {fg};
                border-radius: 8px;
                color: {fg};
                font-family: {FONT_STACK};
                font-size: 13px;
                padding: 8px 16px;
            }}
        """)
        self.setText(text)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()

        self._fade_anim.setDuration(FADE_IN_MS)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

        self._dismiss_timer.start(TOAST_DURATION_MS)


    def _fade_out(self):
        """Handle fade out."""
        self._fade_anim.setDuration(FADE_OUT_MS)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_done)
        self._fade_anim.start()

    def _on_fade_done(self):
        """Handle fade done callbacks."""
        self._fade_anim.finished.disconnect(self._on_fade_done)
        self.hide()

    def _reposition(self):
        """Handle reposition."""
        if self.parent() is None:
            return
        pw = self.parent().width()
        ph = self.parent().height()
        tw = self.width()
        th = self.height()
        x = (pw - tw) // 2
        y = ph - th - MARGIN_BOTTOM - self._bottom_clearance
        y = max(8, y)
        self.move(x, y)

    def resizeEvent(self, event):
        """Handle the resize event."""
        super().resizeEvent(event)
        self._reposition()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
