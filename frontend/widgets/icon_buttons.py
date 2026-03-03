"""
widgets/icon_buttons.py — MicButton (custom paint) + SendButton (custom paint)

Both buttons are 32×32 circle widgets drawn entirely with QPainter.
No emoji, no text — pure line-art icons with 1.5 px stroke weight.

MicButton states:   idle / hover / pressed / listening / disabled
SendButton states:  enabled / hover / pressed / disabled

Listening state: soft sine-wave pulsing ring — subtle, not neon.
HiDPI: all coordinates are floating-point; Qt scales paintEvent automatically.
"""

from PyQt6.QtCore    import (Qt, QPropertyAnimation, QEasingCurve,
                              QRectF, QPointF, pyqtProperty)
from PyQt6.QtGui     import (QPainter, QPainterPath, QPen, QBrush, QColor)
from PyQt6.QtWidgets import QAbstractButton, QSizePolicy

from theme import ThemeManager

SIZE = 32



class _CircleBase(QAbstractButton):
    """
    Checkable-capable circle button with full custom paint.
    Subclasses implement _draw_icon(painter, cx, cy, icon_color).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(SIZE, SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._tokens  = ThemeManager.tokens()
        self._hovered = False

        ThemeManager.subscribe(self._on_theme)

    def _on_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()


    def _is_listening(self) -> bool:
        return self.isCheckable() and self.isChecked()

    def _bg_and_border(self):
        t = self._tokens
        if not self.isEnabled():
            bg = QColor(t['bg.elevated'])
            bg.setAlphaF(0.4)
            bd = QColor(t['border.subtle'])
            return bg, bd
        if self._is_listening():
            bg = QColor(t['accent.subtleBg'])
            bd = QColor(t['accent.primary'])
            return bg, bd
        if self.isDown():
            bg = QColor(t['bg.elevated'])
            bd = QColor(t['border.strong'])
            return bg, bd
        if self._hovered:
            bg = QColor(t['bg.elevated'])
            bd = QColor(t['border.strong'])
            return bg, bd
        bg = QColor(t['bg.elevated'])
        bg.setAlphaF(0.65)
        bd = QColor(t['border.subtle'])
        return bg, bd

    def _icon_color(self) -> QColor:
        t = self._tokens
        if not self.isEnabled():
            c = QColor(t['text.muted'])
            c.setAlphaF(0.35)
            return c
        if self._is_listening():
            return QColor(t['accent.primary'])
        if self._hovered or self.isDown():
            return QColor(t['text.primary'])
        return QColor(t['text.secondary'])


    def paintEvent(self, _event):
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = SIZE / 2.0
        cy = SIZE / 2.0
        r  = SIZE / 2.0 - 1.5

        bg, bd = self._bg_and_border()
        p.setPen(QPen(bd, 1.0))
        p.setBrush(QBrush(bg))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        self._draw_icon(p, cx, cy, self._icon_color())
        p.end()

    def _draw_icon(self, p: QPainter, cx: float, cy: float, color: QColor):
        raise NotImplementedError


    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass



class MicButton(_CircleBase):
    """
    Microphone icon built from QPainterPath primitives.

    Geometry (32×32 canvas, centre = 16, 16):
      Capsule body : RoundedRect(cx-3.5, cy-8,  7, 11)  r=3.5
      Stand arc    : Arc of ellipse(cx-6, cy+1, 12,  7)  bottom half (U shape)
      Vertical post: (cx, cy+8)  → (cx, cy+11)
      Base bar     : (cx-4, cy+11) → (cx+4, cy+11)

    Listening: animated sine ring expands from button radius outward.
    Stroke weight: 1.5 px — matches SendButton arrow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setToolTip("Click to start voice input")

        self._ring_alpha: float = 0.0
        self._ring_scale: float = 1.0

        self._anim_alpha = QPropertyAnimation(self, b"ring_alpha", self)
        self._anim_alpha.setDuration(1200)
        self._anim_alpha.setLoopCount(-1)
        self._anim_alpha.setKeyValueAt(0.0, 0.40)
        self._anim_alpha.setKeyValueAt(0.5, 0.0)
        self._anim_alpha.setKeyValueAt(1.0, 0.40)
        self._anim_alpha.setEasingCurve(QEasingCurve.Type.SineCurve)

        self._anim_scale = QPropertyAnimation(self, b"ring_scale", self)
        self._anim_scale.setDuration(1200)
        self._anim_scale.setLoopCount(-1)
        self._anim_scale.setKeyValueAt(0.0, 1.0)
        self._anim_scale.setKeyValueAt(0.5, 1.40)
        self._anim_scale.setKeyValueAt(1.0, 1.0)
        self._anim_scale.setEasingCurve(QEasingCurve.Type.SineCurve)

        self.toggled.connect(self._on_toggled)


    def _get_ring_alpha(self) -> float:
        return self._ring_alpha

    def _set_ring_alpha(self, v: float):
        self._ring_alpha = v
        self.update()

    def _get_ring_scale(self) -> float:
        return self._ring_scale

    def _set_ring_scale(self, v: float):
        self._ring_scale = v
        self.update()

    ring_alpha = pyqtProperty(float, _get_ring_alpha, _set_ring_alpha)
    ring_scale = pyqtProperty(float, _get_ring_scale, _set_ring_scale)

    def _on_toggled(self, checked: bool):
        if checked:
            self._anim_alpha.start()
            self._anim_scale.start()
        else:
            self._anim_alpha.stop()
            self._anim_scale.stop()
            self._ring_alpha = 0.0
            self._ring_scale = 1.0
            self.update()


    def paintEvent(self, event):
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = SIZE / 2.0
        cy = SIZE / 2.0
        ring_base_r = 8.8

        if self._is_listening() and self._ring_alpha > 0.0:
            ring_r = ring_base_r * self._ring_scale
            rc     = QColor(self._tokens['accent.primary'])
            rc.setAlphaF(self._ring_alpha)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(rc, 1.0))
            p.drawEllipse(QRectF(cx - ring_r, cy - ring_r,
                                 ring_r * 2, ring_r * 2))

        self._draw_icon(p, cx, cy, self._icon_color())
        p.end()

    def _draw_icon(self, p: QPainter, cx: float, cy: float, color: QColor):
        pen = QPen(color, 1.6, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        body = QPainterPath()
        body.addRoundedRect(QRectF(cx - 3.0, cy - 7.5, 6.0, 10.0), 3.0, 3.0)
        p.drawPath(body)

        p.drawArc(QRectF(cx - 6.0, cy + 0.2, 12.0, 7.2),
                  0 * 16, -180 * 16)

        p.drawLine(QPointF(cx, cy + 7.6), QPointF(cx, cy + 10.2))

        p.drawLine(QPointF(cx - 3.8, cy + 10.2), QPointF(cx + 3.8, cy + 10.2))



class SendButton(_CircleBase):
    """
    Modern send button — solid accent circle with a clean upward-arrow glyph.

    Disabled : same accent circle at 28% opacity, white arrow at 45% opacity.
               Reads as "same button, not yet active" — not a different widget.
    Enabled  : full accent fill, white arrow.
    Hover    : accent.hover fill.
    Pressed  : accent.pressed fill.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEnabled(False)


    _AMBER         = "#E8A020"
    _AMBER_HOVER   = "#F0B040"
    _AMBER_PRESSED = "#C88010"

    def _circle_color(self) -> QColor:
        if not self.isEnabled():
            c = QColor(self._AMBER)
            c.setAlphaF(0.28)
            return c
        if self.isDown():
            return QColor(self._AMBER_PRESSED)
        if self._hovered:
            return QColor(self._AMBER_HOVER)
        return QColor(self._AMBER)

    def _icon_color(self) -> QColor:
        if not self.isEnabled():
            c = QColor('#FFFFFF')
            c.setAlphaF(0.45)
            return c
        return QColor('#FFFFFF')


    def paintEvent(self, _event):
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = SIZE / 2.0
        cy = SIZE / 2.0
        r  = SIZE / 2.0 - 1.5

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._circle_color()))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        self._draw_icon(p, cx, cy, self._icon_color())
        p.end()

    def _draw_icon(self, p: QPainter, cx: float, cy: float, color: QColor):
        """
        Upward arrow: filled triangle head + rounded-rect stem.
        Vertically centred with a slight upward bias for optical balance.
        """
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))

        head = QPainterPath()
        head.moveTo(cx,        cy - 5.6)        
        head.lineTo(cx - 4.0,  cy - 0.8)                
        head.lineTo(cx + 4.0,  cy - 0.8)                 
        head.closeSubpath()
        p.drawPath(head)

        stem = QPainterPath()
        stem.addRoundedRect(QRectF(cx - 1.55, cy - 0.8, 3.1, 6.2), 1.55, 1.55)
        p.drawPath(stem)