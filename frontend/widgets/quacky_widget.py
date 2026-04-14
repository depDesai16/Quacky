import math
import random
import threading
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

# Public API

_pop_requested = threading.Event()
_reset_requested = threading.Event()


def pop_bubble():
    _pop_requested.set()


def reset_bubble():
    _reset_requested.set()


class QuackyBubble(QWidget):
    """Sprite-frame duck widget with pop animation."""

    W, H = 380, 380
    BX, BY = 190, 190

    DUCK_SIZE = 230.0
    POP_RADIUS = 104.0

    FLOAT_AMP = 7.0
    FLOAT_FREQ = 4.0
    FPS = 60

    FLAP_PERIOD = 4500
    BLINK_EVERY = 4000
    BLINK_DUR = 150
    LOOK_MOVE = 600
    LOOK_HOLD_LO = 1500
    LOOK_HOLD_HI = 3500

    _SITTING_FRAME: QPixmap | None = None
    _SITTING_FRAME_CROPPED: QPixmap | None = None

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
        self._duck_opacity = 1.0

        self._fragments = self._make_fragments()

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // self.FPS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @staticmethod
    def draw_static_graphic(painter, cx, cy, scale=1.0):
        """Draw static duck frame on any painter."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.translate(cx, cy)
        painter.scale(scale, scale)
        QuackyBubble._draw_duck(painter, 0, 0)
        painter.restore()

    @staticmethod
    def _get_sitting_frame() -> QPixmap | None:
        """Load and cache sprite frame sit_r9_c3 (row 9, col 3)."""
        if QuackyBubble._SITTING_FRAME is not None:
            return QuackyBubble._SITTING_FRAME

        sprite_path = (
            Path(__file__).resolve().parent.parent
            / "animations"
            / "duck_spritesheet.png"
        )
        sheet = QPixmap(str(sprite_path))
        if sheet.isNull():
            return None

        QuackyBubble._SITTING_FRAME = sheet.copy(3 * 32, 9 * 32, 32, 32)
        return QuackyBubble._SITTING_FRAME

    @staticmethod
    def _get_sitting_frame_cropped() -> QPixmap | None:
        """Return the sprite frame cropped to visible alpha bounds."""
        if QuackyBubble._SITTING_FRAME_CROPPED is not None:
            return QuackyBubble._SITTING_FRAME_CROPPED

        frame = QuackyBubble._get_sitting_frame()
        if frame is None or frame.isNull():
            return None

        img = frame.toImage()
        min_x, min_y = img.width(), img.height()
        max_x, max_y = -1, -1

        for y in range(img.height()):
            for x in range(img.width()):
                if img.pixelColor(x, y).alpha() > 0:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            QuackyBubble._SITTING_FRAME_CROPPED = frame
        else:
            QuackyBubble._SITTING_FRAME_CROPPED = frame.copy(
                min_x,
                min_y,
                max_x - min_x + 1,
                max_y - min_y + 1,
            )

        return QuackyBubble._SITTING_FRAME_CROPPED

    def _tick(self):
        dt = 1000 // self.FPS

        if _reset_requested.is_set():
            _reset_requested.clear()
            self._state = "idle"
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
                self._blink_t = -1
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
            self._gaze_tx = random.uniform(-0.55, 0.55)
            self._gaze_ty = random.uniform(-0.35, 0.45)
            self._gaze_start = self._t
            self._gaze_hold_until = (
                self._t
                + self.LOOK_MOVE
                + random.randint(self.LOOK_HOLD_LO, self.LOOK_HOLD_HI)
            )

    def _flap(self):
        return math.sin((self._t / self.FLAP_PERIOD) * 2 * math.pi) * 16

    def _update_pop(self, t):
        if t < 0.18:
            self._duck_opacity = max(0.0, 1.0 - (t / 0.18) ** 1.5)
        else:
            self._duck_opacity = 0.0

        if t >= 0.90:
            self._state = "done"

    def _make_fragments(self):
        rng = random.Random(42)
        palette = [
            QColor(246, 244, 238),  # off-white
            QColor(233, 228, 216),  # warm off-white
            QColor(214, 165, 124),  # dull orange
            QColor(194, 143, 103),  # darker dull orange
        ]
        n = 22
        return [
            {
                "angle": 2 * math.pi * i / n + rng.uniform(-0.2, 0.2),
                "dist": rng.uniform(self.POP_RADIUS * 0.7, self.POP_RADIUS * 1.4),
                "size": rng.uniform(3, 8),
                "alpha": rng.uniform(0.55, 1.0),
                "color": rng.choice(palette),
            }
            for i in range(n)
        ]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        dy = (
            math.sin(self._float_ms / 1000.0 * 2 * math.pi / self.FLOAT_FREQ)
            * self.FLOAT_AMP
            if self._state == "idle"
            else 0.0
        )
        cy = self.BY + dy

        p.setOpacity(self._duck_opacity)
        self._draw_duck(
            p,
            self.BX,
            cy,
            self._flap(),
            self._blink_scale(),
            self._gaze_x,
            self._gaze_y,
        )

        if self._state == "popping":
            p.setOpacity(1.0)
            self._draw_pop(p, cy)

        p.setOpacity(1.0)
        p.end()

    def _blink_scale(self):
        if self._blink_t < 0:
            return 1.0
        pulse = self._blink_t / self.BLINK_DUR
        return 1.0 - pulse / 0.5 if pulse < 0.5 else (pulse - 0.5) / 0.5

    @staticmethod
    def _draw_duck(p, cx, cy, flap=0.0, bs=1.0, gaze_x=0.0, gaze_y=0.0):
        frame = QuackyBubble._get_sitting_frame()
        if frame is None or frame.isNull():
            return

        bob = -2 if flap > 7 else (2 if flap < -7 else 0)
        draw_size = QuackyBubble.DUCK_SIZE
        x = cx - (draw_size / 2.0)
        y = cy - (draw_size / 2.0) + bob
        p.drawPixmap(QRectF(x, y, draw_size, draw_size), frame, QRectF(0, 0, 32, 32))

    def _draw_pop(self, p, cy):
        t = self._pop_ms / 1000.0
        bx = self.BX

        frag_start, frag_dur = 0.03, 0.62
        p.setPen(Qt.PenStyle.NoPen)
        for frag in self._fragments:
            ft = t - frag_start
            if ft <= 0:
                continue
            prog = min(ft / frag_dur, 1.0)
            ease = 1.0 - (1.0 - prog) ** 2
            dist = frag["dist"] * ease
            fx = bx + math.cos(frag["angle"]) * dist
            fy = cy + math.sin(frag["angle"]) * dist
            size = frag["size"] * (1.0 - prog * 0.65)
            fade = max(0.0, 1.0 - max(0.0, (prog - 0.50) / 0.50))
            col = QColor(frag["color"])
            col.setAlpha(int(frag["alpha"] * fade * 255))
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(fx, fy), size, size)


def get_quacky_icon() -> QIcon:
    """Render app/tray icon from sit_r9_c3 frame with tight crop and size variants."""
    frame = QuackyBubble._get_sitting_frame_cropped()
    if frame is None or frame.isNull():
        fallback = QPixmap(256, 256)
        fallback.fill(QColor(0, 0, 0, 0))
        painter = QPainter(fallback)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        QuackyBubble.draw_static_graphic(painter, 128.0, 128.0, scale=1.0)
        painter.end()
        return QIcon(fallback)

    icon = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        pad = 0 if size <= 24 else 1
        target = QRectF(pad, pad, size - (2 * pad), size - (2 * pad))
        painter.drawPixmap(
            target,
            frame,
            QRectF(0, 0, frame.width(), frame.height()),
        )
        painter.end()
        icon.addPixmap(pm)

    return icon
