"""
widgets/card_widget.py — Redesigned CardWidget.

Replaces the original cardwidget.py.
Key differences from original:
  - Border is 1 px, rgba(255,255,255,0.07) — not the old harsh gold line.
  - Background comes from theme token bg.surface.
  - QGraphicsDropShadowEffect replaces any painted shadow.
  - Theme-aware via apply_theme(tokens).
"""

import sys

from PyQt6.QtCore    import Qt, QRectF
from PyQt6.QtGui     import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtWidgets import QWidget, QGraphicsDropShadowEffect

from theme import ThemeManager


class CardWidget(QWidget):
    RADIUS = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._tokens = ThemeManager.tokens()
        self._setup_shadow()

        ThemeManager.subscribe(self.apply_theme)


    def _setup_shadow(self):
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
        self._tokens = tokens
        self._setup_shadow()
        self.update()


    def paintEvent(self, event):
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

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
