import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath


class QuackyWidget(QWidget):
    SIZE = 300

    FPS          = 60
    FLAP_PERIOD  = 4500
    BLINK_EVERY  = 4000
    BLINK_DUR    = 150

    # Look-around timing
    LOOK_MOVE_DUR  = 600    # ms to slide pupils to new position
    LOOK_HOLD_MIN  = 1500   # ms to hold gaze
    LOOK_HOLD_MAX  = 3500

    # Icon → widget transform
    S  = 1.75
    DX = 66.0
    DY = 17.5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._t          = 0
        self._blink_t    = -1
        self._next_blink = self.BLINK_EVERY

        # Gaze: offset of pupils within eye white, range roughly -1..1
        self._gaze_x     = 0.0
        self._gaze_y     = 0.0
        self._gaze_tx    = 0.0   # target
        self._gaze_ty    = 0.0
        self._gaze_start = 0
        self._gaze_hold_until = self.LOOK_HOLD_MIN

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // self.FPS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ── Timer ─────────────────────────────────
    def _tick(self):
        dt = 1000 // self.FPS
        self._t += dt

        # Blink
        if self._blink_t >= 0:
            self._blink_t += dt
            if self._blink_t > self.BLINK_DUR:
                self._blink_t    = -1
                self._next_blink = self._t + self.BLINK_EVERY
        elif self._t >= self._next_blink:
            self._blink_t = 0

        # Gaze movement
        move_elapsed = self._t - self._gaze_start
        if move_elapsed < self.LOOK_MOVE_DUR:
            # Smooth ease-in-out lerp toward target
            prog = move_elapsed / self.LOOK_MOVE_DUR
            ease = prog * prog * (3 - 2 * prog)   # smoothstep
            self._gaze_x = self._gaze_x + (self._gaze_tx - self._gaze_x) * ease
            self._gaze_y = self._gaze_y + (self._gaze_ty - self._gaze_y) * ease
        elif self._t >= self._gaze_hold_until:
            # Pick a new random gaze target
            self._gaze_tx        = random.uniform(-0.55, 0.55)
            self._gaze_ty        = random.uniform(-0.35, 0.45)
            self._gaze_start     = self._t
            self._gaze_hold_until = (self._t + self.LOOK_MOVE_DUR
                                     + random.randint(self.LOOK_HOLD_MIN, self.LOOK_HOLD_MAX))

        self.update()

    # ── Animation helpers ─────────────────────
    def _flap_angle(self):
        phase = (self._t / self.FLAP_PERIOD) * 2 * math.pi
        return math.sin(phase) * 18

    def _blink_scale(self):
        if self._blink_t < 0:
            return 1.0
        prog = self._blink_t / self.BLINK_DUR
        return 1.0 - (prog / 0.5) if prog < 0.5 else (prog - 0.5) / 0.5

    # ── Coord helpers ─────────────────────────
    def _t2(self, x, y):
        return QPointF(x * self.S + self.DX, y * self.S + self.DY)

    def _r(self, x, y, w, h):
        pt = self._t2(x, y)
        return QRectF(pt.x(), pt.y(), w * self.S, h * self.S)

    # ── Paint ─────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_legs(p)
        self._draw_feet(p)
        self._draw_body(p)
        self._draw_wings(p)
        self._draw_head(p)
        self._draw_cheeks(p)
        self._draw_eyes(p)
        self._draw_bill(p)
        self._draw_tuft(p)

        p.end()

    # ── Body ──────────────────────────────────
    def _draw_body(self, p):
        cx, cy = self.SIZE / 2, 196
        bw, bh = 118, 140

        p.setBrush(QBrush(QColor("#FFD700")))
        p.setPen(QPen(QColor("#CC9900"), 2))
        p.drawEllipse(QRectF(cx - bw/2, cy - bh/2, bw, bh))

        p.setBrush(QBrush(QColor("#FFF0A0")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - 34, cy - 46, 68, 90))

    # ── Wings ─────────────────────────────────
    def _draw_wings(self, p):
        angle = self._flap_angle()
        cx    = self.SIZE / 2
        bw    = 53

        for side in (-1, 1):
            pivot_x = cx + side * (bw - 2)
            pivot_y = 172

            p.save()
            p.translate(pivot_x, pivot_y)
            p.rotate(side * angle)

            p.setBrush(QBrush(QColor("#FFC400")))
            p.setPen(QPen(QColor("#CC9900"), 1.5))

            wing = QPainterPath()
            wing.moveTo(0, 0)
            wing.cubicTo(side*32, -18, side*50,  16, side*22,  46)
            wing.cubicTo(side*6,   52, side*-8,  28, 0,         0)
            p.drawPath(wing)
            p.restore()

    # ── Legs — longer so they visually connect to feet ──
    def _draw_legs(self, p):
        p.setBrush(QBrush(QColor("#FF8C00")))
        p.setPen(QPen(QColor("#CC6000"), 1.5))

        cx         = self.SIZE / 2
        leg_top_y  = 258
        leg_bot_y  = 284   # extended down to meet feet
        leg_w      = 14

        for side in (-1, 1):
            lx = cx + side * 24
            p.drawRoundedRect(
                QRectF(lx - leg_w/2, leg_top_y, leg_w, leg_bot_y - leg_top_y),
                5, 5
            )

    # ── Feet — webbed, positioned at leg bottom ───
    def _draw_feet(self, p):
        p.setBrush(QBrush(QColor("#FF8C00")))
        p.setPen(QPen(QColor("#CC6000"), 1.5))

        cx     = self.SIZE / 2
        foot_y = 280   # matches leg_bot_y

        for side in (-1, 1):
            fx = cx + side * 24

            foot = QPainterPath()
            toes = [
                (fx + side * -10, foot_y + 18),
                (fx + side *   4, foot_y + 22),
                (fx + side *  18, foot_y + 16),
            ]

            foot.moveTo(fx - side * 4, foot_y + 2)
            foot.cubicTo(
                fx + side * -14, foot_y + 8,
                toes[0][0] - side * 2, toes[0][1] - 4,
                toes[0][0], toes[0][1]
            )
            foot.cubicTo(
                toes[0][0] + side * 4, toes[0][1] + 2,
                toes[1][0] - side * 4, toes[1][1] + 2,
                toes[1][0], toes[1][1]
            )
            foot.cubicTo(
                toes[1][0] + side * 4, toes[1][1] + 2,
                toes[2][0] - side * 4, toes[2][1] + 2,
                toes[2][0], toes[2][1]
            )
            foot.cubicTo(
                toes[2][0] + side * 2, toes[2][1] - 6,
                fx + side * 16, foot_y + 4,
                fx - side * 4, foot_y + 2
            )
            foot.closeSubpath()
            p.drawPath(foot)

            p.setPen(QPen(QColor("#CC6000"), 1.0))
            for tx, ty in toes:
                p.drawLine(QPointF(fx, foot_y + 6), QPointF(tx, ty))
            p.setPen(QPen(QColor("#CC6000"), 1.5))

    # ── Head ──────────────────────────────────
    def _draw_head(self, p):
        p.setBrush(QBrush(QColor("#FFD700")))
        p.setPen(QPen(QColor("#CC9900"), 2))
        p.drawEllipse(self._r(9, 6, 78, 78))

    # ── Cheeks ────────────────────────────────
    def _draw_cheeks(self, p):
        p.setBrush(QBrush(QColor("#FFBE00")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self._r(6, 45, 24, 18))
        p.drawEllipse(self._r(66, 45, 24, 18))

    # ── Eyes — blink + look-around ────────────
    def _draw_eyes(self, p):
        bs = self._blink_scale()

        for lx, px_icon in [(19, 19), (53, 53)]:
            # Eye white
            r = self._r(lx, 24, 24, 27)
            r_blink = QRectF(r.x(), r.center().y() - r.height()/2 * bs,
                             r.width(), r.height() * bs)
            p.setBrush(QBrush(QColor("#FFFFFF")))
            p.setPen(QPen(QColor("#CCAA00"), 1.5))
            p.drawEllipse(r_blink)

            if bs > 0.15:
                # Max pupil travel within the white
                travel_x = r.width()  * 0.22
                travel_y = r.height() * 0.18

                # Pupil centre — gaze offset applied
                rp       = self._r(px_icon + 8, 31, 12, 14)
                pupil_cx = rp.center().x() + self._gaze_x * travel_x
                pupil_cy = rp.center().y() + self._gaze_y * travel_y
                ph       = rp.height() * bs
                pw       = rp.width()

                p.setBrush(QBrush(QColor("#1a1a2e")))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(pupil_cx - pw/2, pupil_cy - ph/2, pw, ph))

                # Shine — follows pupil
                shine_size = self._r(px_icon + 11, 33, 5, 5).width()
                sx = pupil_cx + pw * 0.15
                sy = pupil_cy - ph * 0.2
                p.setBrush(QBrush(QColor("#FFFFFF")))
                p.drawEllipse(QRectF(sx, sy, shine_size, shine_size * bs))

    # ── Bill ──────────────────────────────────
    def _draw_bill(self, p):
        p.setBrush(QBrush(QColor("#FF8C00")))
        p.setPen(QPen(QColor("#CC6000"), 2))

        bill = QPainterPath()
        m = self._t2(48, 54)
        bill.moveTo(m.x(), m.y())
        c1 = self._t2(30, 51); c2 = self._t2(27, 66); e1 = self._t2(48, 68)
        bill.cubicTo(c1.x(), c1.y(), c2.x(), c2.y(), e1.x(), e1.y())
        c3 = self._t2(69, 66); c4 = self._t2(66, 51); e2 = self._t2(48, 54)
        bill.cubicTo(c3.x(), c3.y(), c4.x(), c4.y(), e2.x(), e2.y())
        p.drawPath(bill)

        p.setPen(QPen(QColor("#CC6000"), 1.8))
        a = self._t2(33, 60); b = self._t2(63, 60)
        p.drawLine(a, b)

    # ── Tuft ──────────────────────────────────
    def _draw_tuft(self, p):
        p.setBrush(QBrush(QColor("#FFD700")))
        p.setPen(QPen(QColor("#CC9900"), 1.5))

        tuft = QPainterPath()
        m = self._t2(42, 9)
        tuft.moveTo(m.x(), m.y())
        c1 = self._t2(39, -3); c2 = self._t2(48, -6); e1 = self._t2(48, 5)
        tuft.cubicTo(c1.x(), c1.y(), c2.x(), c2.y(), e1.x(), e1.y())
        c3 = self._t2(48, -6); c4 = self._t2(57, -3); e2 = self._t2(54, 9)
        tuft.cubicTo(c3.x(), c3.y(), c4.x(), c4.y(), e2.x(), e2.y())
        p.drawPath(tuft)