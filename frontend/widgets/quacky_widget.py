import math
import random
import threading
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QPainterPath,
                          QRadialGradient, QIcon, QPixmap, QPainter, QColor)

## Public API

_pop_requested = threading.Event()
_reset_requested = threading.Event()

def pop_bubble():
    _pop_requested.set()

def reset_bubble():
    _reset_requested.set()

def get_quacky_icon() -> QIcon:
        """Renders a tightly cropped QuackyBubble graphic to maximize tray size."""
        # Adjust to trim space in tray. Effectively adjusting logo size.
        # Right now 325 is smallest (largest image) without clipping.
        canvas_size = 325
        
        pixmap = QPixmap(canvas_size, canvas_size)
        pixmap.fill(QColor(0, 0, 0, 0)) # Transparent background
        painter = QPainter(pixmap)
        
        # Render the graphic perfectly centered in our new tight canvas
        center = canvas_size / 2.0
        QuackyBubble.draw_static_graphic(painter, center, center, scale=1.0)
        painter.end()
        
        return QIcon(pixmap)

## QuackiBubble

class QuackyBubble(QWidget):
    """Drop-in PyQt6 widget for the Quacki glass bubble logo."""

    W, H = 380, 440
    BX, BY = 190, 200
    BR = 152

    FLOAT_AMP = 9.0
    FLOAT_FREQ = 4.0
    FPS = 60

    FLAP_PERIOD = 4500
    BLINK_EVERY = 4000
    BLINK_DUR = 150
    LOOK_MOVE = 600
    LOOK_HOLD_LO = 1500
    LOOK_HOLD_HI = 3500

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._t = 0
        self._blink_t = -1
        self._next_blink = self.BLINK_EVERY

        self._gaze_x = self._gaze_y = 0.0
        self._gaze_tx = self._gaze_ty = 0.0
        self._gaze_start = 0
        self._gaze_hold_until = self.LOOK_HOLD_LO

        self._float_ms = 0
        self._state = "idle"
        self._pop_ms = 0
        self._bubble_scale = 1.0
        self._bubble_alpha = 1.0
        self._duck_opacity = 1.0

        self._fragments = self._make_fragments()

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // self.FPS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()


    ## Public Static Drawer

    @staticmethod
    def draw_static_graphic(painter, cx, cy, scale=1.0):
        """
        Draws a static, idle version of the bubble and duck on any QPainter.
        Allows the graphic to be used in icons, pixmaps, or other widgets.
        """
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(cx, cy)
        painter.scale(scale, scale)
        br = QuackyBubble.BR
        
        # Draw everything centered at 0,0 since we translated the painter
        QuackyBubble._draw_glow(painter, 0, 0, br)
        QuackyBubble._draw_bubble(painter, 0, 0, br)
        QuackyBubble._draw_duck(painter, 0, 0) # Defaults to flap=0, gaze=0
        QuackyBubble._draw_shine(painter, 0, 0, br)

        painter.restore()


    ## Tick & Logic

    def _tick(self):
        dt = 1000 // self.FPS

        if _reset_requested.is_set():
            _reset_requested.clear()
            self._state = "idle"
            self._bubble_scale = 1.0
            self._bubble_alpha = 1.0
            self._duck_opacity = 1.0

        if _pop_requested.is_set() and self._state == "idle":
            _pop_requested.clear()
            self._state = "popping"
            self._pop_ms = 0

        self._t += dt
        self._float_ms += dt if self._state == "idle" else 0

        self._tick_blink(dt)
        self._tick_gaze(dt)

        if self._state == "popping":
            self._pop_ms += dt
            self._update_pop(self._pop_ms / 1000.0)

        self.update()

    def _tick_blink(self, dt):
        if self._blink_t >= 0:
            self._blink_t += dt
            if self._blink_t > self.BLINK_DUR:
                self._blink_t    = -1
                self._next_blink = self._t + self.BLINK_EVERY
        elif self._t >= self._next_blink:
            self._blink_t = 0

    def _tick_gaze(self, dt):
        elapsed = self._t - self._gaze_start
        if elapsed < self.LOOK_MOVE:
            prog = elapsed / self.LOOK_MOVE
            ease = prog * prog * (3 - 2 * prog)
            self._gaze_x += (self._gaze_tx - self._gaze_x) * ease
            self._gaze_y += (self._gaze_ty - self._gaze_y) * ease
        elif self._t >= self._gaze_hold_until:
            self._gaze_tx         = random.uniform(-0.55, 0.55)
            self._gaze_ty         = random.uniform(-0.35, 0.45)
            self._gaze_start      = self._t
            self._gaze_hold_until = (self._t + self.LOOK_MOVE
                                     + random.randint(self.LOOK_HOLD_LO, self.LOOK_HOLD_HI))

    def _flap(self):
        return math.sin((self._t / self.FLAP_PERIOD) * 2 * math.pi) * 16

    def _blink_scale(self):
        if self._blink_t < 0: return 1.0
        p = self._blink_t / self.BLINK_DUR
        return 1.0 - p / 0.5 if p < 0.5 else (p - 0.5) / 0.5

    def _update_pop(self, t):
        if t < 0.18:
            self._bubble_scale = 1.0 + (t / 0.18) * 0.22
            self._bubble_alpha = max(0.0, 1.0 - (t / 0.18) ** 1.5)
            self._duck_opacity = self._bubble_alpha
        else:
            self._bubble_scale = 1.22
            self._bubble_alpha = 0.0
            self._duck_opacity = 0.0
        
        if t >= 0.90: self._state = "done"

    def _make_fragments(self):
        rng = random.Random(42)
        palette = [
            QColor(200, 225, 255), QColor(255, 255, 255),
            QColor(150, 200, 255), QColor(255, 212, 67),
            QColor(180, 215, 255),
        ]
        N = 22
        return [{
            'angle': 2 * math.pi * i / N + rng.uniform(-0.2, 0.2),
            'dist': rng.uniform(self.BR * 0.85, self.BR * 1.55),
            'size': rng.uniform(4, 11),
            'alpha': rng.uniform(0.55, 1.0),
            'color': rng.choice(palette),
        } for i in range(N)]


    ## Paint

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        dy = (math.sin(self._float_ms / 1000.0 * 2 * math.pi / self.FLOAT_FREQ)
              * self.FLOAT_AMP if self._state == "idle" else 0.0)
        cy = self.BY + dy
        br = self.BR * self._bubble_scale

        self._draw_glow(p, self.BX, cy, self.BR)

        p.setOpacity(self._bubble_alpha)
        self._draw_bubble(p, self.BX, cy, br)

        p.setOpacity(self._duck_opacity)
        self._draw_duck(p, self.BX, cy, self._flap(), self._blink_scale(), self._gaze_x, self._gaze_y)

        p.setOpacity(self._bubble_alpha * 0.85)
        self._draw_shine(p, self.BX, cy, br)

        if self._state == "popping":
            p.setOpacity(1.0)
            self._draw_pop(p, cy)

        p.setOpacity(1.0)
        p.end()


    ## Static Drawing Helpers

    @staticmethod
    def _draw_glow(p, cx, cy, br):
        for rf, a in [(1.24, 28), (1.20, 50), (0.88, 70)]:
            r = br * rf
            grd = QRadialGradient(cx, cy, r)
            grd.setColorAt(0.0, QColor(80, 140, 255, a))
            grd.setColorAt(1.0, QColor(80, 140, 255, 0))
            p.setBrush(QBrush(grd))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)

    @staticmethod
    def _draw_bubble(p, cx, cy, br):
        grd = QRadialGradient(cx - br*0.18, cy - br*0.22, br*0.35, cx, cy, br)
        grd.setColorAt(0.0, QColor(160, 205, 255, 55))
        grd.setColorAt(0.5, QColor(100, 165, 255, 30))
        grd.setColorAt(1.0, QColor(50,  110, 220, 18))
        p.setBrush(QBrush(grd))
        p.setPen(QPen(QColor(255, 255, 255, 80), 1.8))
        p.drawEllipse(QPointF(cx, cy), br, br)

        p.setPen(QPen(QColor(140, 190, 255, 35), 3.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), br - 2, br - 2)

        grd2 = QRadialGradient(cx, cy + br*0.75, br*0.38)
        grd2.setColorAt(0.0, QColor(255, 255, 255, 40))
        grd2.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(grd2))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy + br*0.75), br*0.38, br*0.14)

    @staticmethod
    def _draw_shine(p, cx, cy, br):
        """Draws a crisp crescent reflection for a more realistic glass look."""
        # Soft interior volume glaze
        grd = QRadialGradient(cx - br*0.3, cy - br*0.3, br*1.2)
        grd.setColorAt(0.0, QColor(255, 255, 255, 60))
        grd.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(grd))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), br, br)

        # Sharp crescent arcs
        rect = QRectF(cx - br*0.82, cy - br*0.82, br*1.64, br*1.64)
        
        pen = QPen(QColor(255, 255, 255, 200))
        pen.setWidthF(br * 0.06)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Top-left reflection (Angles are in 1/16ths of a degree)
        p.drawArc(rect, 105 * 16, 65 * 16)

        # Bottom-right secondary reflection
        pen.setColor(QColor(255, 255, 255, 80))
        pen.setWidthF(br * 0.03)
        p.setPen(pen)
        p.drawArc(rect, -65 * 16, 45 * 16)

    @staticmethod
    def _draw_duck(p, cx, cy, flap=0.0, bs=1.0, gaze_x=0.0, gaze_y=0.0):
        ox = cx - 4
        oy = cy + 14

        WHITE = QColor(255, 255, 255, 250)
        BELLY = QColor(190, 220, 248, 190)
        BEAK = QColor(255, 200, 40, 255)
        BEAK_S = QColor(220, 155, 10, 120)
        STROKE = QColor(255, 255, 255, 30)
        EYE_B = QColor(50, 110, 240, 255)
        EYE_W = QColor(255, 255, 255, 255)
        PUPIL = QColor(10, 30, 90, 255)

        p.setPen(QPen(STROKE, 1.2))

        # Tail bump
        p.setBrush(QBrush(WHITE))
        tail = QPainterPath()
        tail.moveTo(ox - 74, oy - 12)
        tail.cubicTo(ox - 88, oy - 40, ox - 68, oy - 62, ox - 50, oy - 52)
        tail.cubicTo(ox - 38, oy - 44, ox - 48, oy - 20, ox - 60, oy - 8)
        tail.closeSubpath()
        p.drawPath(tail)

        # Body
        p.setBrush(QBrush(WHITE))
        p.drawEllipse(QRectF(ox - 88, oy - 46, 172, 98))

        # Belly / Wing
        belly_rock = flap * 0.28
        p.save()
        p.translate(ox - 8, oy + 8)
        p.rotate(belly_rock)
        p.setBrush(QBrush(BELLY))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-52, -26, 104, 52))
        p.restore()

        p.setPen(QPen(STROKE, 1.2))

        # Head
        hcx = ox + 54
        hcy = oy - 58
        hr = 40

        p.setBrush(QBrush(WHITE))
        p.drawEllipse(QRectF(hcx - hr, hcy - hr, hr * 2, hr * 2))

        p.setPen(Qt.PenStyle.NoPen)
        hg = QRadialGradient(hcx - 12, hcy - 16, 18)
        hg.setColorAt(0.0, QColor(255, 255, 255, 100))
        hg.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(hg))
        p.drawEllipse(QRectF(hcx - 24, hcy - 26, 36, 28))

        p.setPen(QPen(STROKE, 1.2))

        # Beak
        bk_x = hcx + hr - 4
        bk_y = hcy + 6
        beak = QPainterPath()
        beak.moveTo(bk_x, bk_y - 9)
        beak.lineTo(bk_x + 28, bk_y + 1)
        beak.lineTo(bk_x, bk_y + 9)
        beak.closeSubpath()
        p.setBrush(QBrush(BEAK))
        p.setPen(QPen(BEAK_S, 0.8))
        p.drawPath(beak)

        # Beak Shine
        shine_pen = QPen(QColor(255, 255, 255, 180), 1.5)
        shine_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(shine_pen)
        # Draw a small angled line matching the top slope of the beak
        p.drawLine(QPointF(bk_x + 5, bk_y - 6.5), QPointF(bk_x + 15, bk_y - 3))

        # Eye
        ex = hcx + 12
        ey = hcy - 8
        er = 9
        p.setBrush(QBrush(EYE_B))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(ex - er, ey - er * bs, er * 2, er * 2 * bs))

        if bs > 0.15:
            travel_x = er * 0.22
            travel_y = er * 0.18
            px_ = ex + gaze_x * travel_x
            py_ = ey + gaze_y * travel_y

            pr = 5.5 * bs
            p.setBrush(QBrush(PUPIL))
            p.drawEllipse(QRectF(px_ - pr + 1, py_ - pr, pr * 2, pr * 2))

            p.setBrush(QBrush(EYE_W))
            cl = 3.0
            p.drawEllipse(QRectF(px_ + 2, py_ - pr * 0.5, cl, cl * bs))


    ## Pop animation

    def _draw_pop(self, p, cy):
        t = self._pop_ms / 1000.0
        bx = self.BX

        if t < 0.40:
            prog = t / 0.40
            # Reduced from 1.5 to 0.18 (Max radius ~179px)
            ring_r = self.BR * (1.0 + prog * 0.18)
            ring_a = int(255 * 0.75 * (1.0 - prog) ** 1.2)
            p.setPen(QPen(QColor(200, 225, 255, ring_a), 2.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(bx, cy), ring_r, ring_r)
            
            if prog > 0.12:
                p2 = (prog - 0.12) / 0.88
                # Reduced from 1.2 to 0.12 (Max radius ~170px)
                ring2_r = self.BR * (1.0 + p2 * 0.12)
                ring2_a = int(255 * 0.35 * (1.0 - p2))
                p.setPen(QPen(QColor(255, 255, 255, ring2_a), 1.2))
                p.drawEllipse(QPointF(bx, cy), ring2_r, ring2_r)

        FRAG_START, FRAG_DUR = 0.03, 0.62
        p.setPen(Qt.PenStyle.NoPen)
        for frag in self._fragments:
            ft = t - FRAG_START
            if ft <= 0: continue
            prog = min(ft / FRAG_DUR, 1.0)
            ease = 1.0 - (1.0 - prog) ** 2
            dist = frag['dist'] * ease
            fx = bx + math.cos(frag['angle']) * dist
            fy = cy + math.sin(frag['angle']) * dist
            size = frag['size'] * (1.0 - prog * 0.65)
            fade = max(0.0, 1.0 - max(0.0, (prog - 0.50) / 0.50))
            col = QColor(frag['color'])
            col.setAlpha(int(frag['alpha'] * fade * 255))
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(fx, fy), size, size)