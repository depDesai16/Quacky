
import sys

from PyQt6.QtCore    import Qt, QRectF
from PyQt6.QtGui     import QPainter, QColor, QPen, QPainterPath, QRegion
from PyQt6.QtWidgets import QWidget, QGraphicsDropShadowEffect

from theme import ThemeManager


class CardWidget(QWidget):
    RADIUS = 14

    def __init__(self, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._tokens = ThemeManager.tokens()
        self._setup_shadow()
        self._update_clip_mask()

        ThemeManager.subscribe(self.apply_theme)


    def _setup_shadow(self):
        """Handle setup shadow."""
        if sys.platform.startswith("win"):
            self.setGraphicsEffect(None)
            return

        t = self._tokens
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        c = QColor(t["shadow.color"])
        c.setAlpha(t["shadow.ambient_alpha"])
        shadow.setColor(c)
        self.setGraphicsEffect(shadow)


    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self._setup_shadow()
        self._update_clip_mask()
        self.update()


    def _update_clip_mask(self):
        """Update clip mask."""
        clip_rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if clip_rect.width() <= 0 or clip_rect.height() <= 0:
            self.clearMask()
            return
        path = QPainterPath()
        path.addRoundedRect(clip_rect, self.RADIUS, self.RADIUS)
        poly = path.toFillPolygon().toPolygon()
        self.setMask(QRegion(poly))


    def paintEvent(self, event):
        """Handle the paint event."""
        t   = self._tokens
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        p.fillPath(path, QColor(t["bg.surface"]))

        pen = QPen(QColor(t["border.subtle"]))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.drawPath(path)

        p.end()

    def resizeEvent(self, event):
        """Handle the resize event."""
        super().resizeEvent(event)
        self._update_clip_mask()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
