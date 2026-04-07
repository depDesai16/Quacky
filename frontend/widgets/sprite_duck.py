"""Sprite-based duck animation widget using a pixel art sprite sheet."""
import math
from pathlib import Path
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPixmap, QTransform, QColor


class SpriteDuck(QWidget):
    """Animated duck using sprite sheet frames."""

    W, H = 380, 440
    SIZE = 380
    FPS = 60

    SPRITE_WIDTH = 32
    SPRITE_HEIGHT = 32

    # (right_row, start_col, num_frames, fps)
    ANIMATIONS = {
        'idle':    (0,  0, 4,  6),   # R=0,  L=1
        'flying':  (11, 0, 10, 12),  # R=11, L=12
        'sitting': (9,  0, 4,  6),   # R=9,  L=10
    }

    LEFT_ROW = {0: 1, 11: 12, 9: 10}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        sprite_path = Path(__file__).parent.parent / "animations" / "duck_spritesheet.png"
        self._sprite_sheet = QPixmap(str(sprite_path))

        self._current_animation = 'idle'
        self._frame_index = 0
        self._frame_timer = 0
        self._t = 0

        self._x = self.W / 2
        self._y = self.H / 2
        self._float_offset = 0.0
        self._scale = 5.5
        self._flip_h = False

        self._state = "idle"
        self._thinking_bob = 0.0
        self._swim_bob_offset = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // self.FPS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_animation(self, name):
        """Switch to a named animation."""
        if name in self.ANIMATIONS and name != self._current_animation:
            self._current_animation = name
            self._frame_index = 0
            self._frame_timer = 0

    def set_swimming_direction(self, angle):
        """Set swimming direction in radians. Pass 0 to stop."""
        if angle != 0:
            self._state = "swimming"
            if self._current_animation != 'flying':
                self.set_animation('flying')
            self._flip_h = abs(math.degrees(angle)) > 90
        else:
            if self._state == "swimming":
                self._state = "idle"
                self.set_animation('idle')
                self._flip_h = False

    def start_thinking(self):
        self._state = "thinking"
        self.set_animation('idle')

    def stop_thinking(self):
        self._state = "idle"
        self.set_animation('idle')

    def _tick(self):
        dt = 1000 // self.FPS
        self._t += dt

        anim = self.ANIMATIONS[self._current_animation]
        _, _, num_frames, anim_fps = anim

        self._frame_timer += dt
        if self._frame_timer >= 1000 / anim_fps:
            self._frame_timer = 0
            self._frame_index = (self._frame_index + 1) % num_frames

        if self._state in ("idle", "thinking"):
            self._float_offset = math.sin(self._t / 1000.0 * 2 * math.pi / 5.0) * 12.0

        self._thinking_bob = (
            math.sin((self._t / 1000.0) * 2 * math.pi) * 25.0
            if self._state == "thinking" else 0.0
        )

        self._swim_bob_offset = (
            math.sin(self._t / 400.0 * 2 * math.pi) * 4.0
            if self._state == "swimming" else 0.0
        )

        self.update()

    def paintEvent(self, event):
        if self._sprite_sheet.isNull():
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        anim = self.ANIMATIONS[self._current_animation]
        base_row, start_col, _, _ = anim
        col = start_col + self._frame_index

        row = self.LEFT_ROW.get(base_row, base_row + 1) if self._flip_h else base_row

        source = QRectF(
            col * self.SPRITE_WIDTH,
            row * self.SPRITE_HEIGHT,
            self.SPRITE_WIDTH,
            self.SPRITE_HEIGHT,
        )

        y_pos = self._y + self._float_offset + self._thinking_bob + self._swim_bob_offset

        p.save()
        p.translate(self._x, y_pos)

        t = QTransform()
        t.scale(self._scale, self._scale)
        p.setTransform(t, True)

        dest = QRectF(
            -self.SPRITE_WIDTH / 2,
            -self.SPRITE_HEIGHT / 2,
            self.SPRITE_WIDTH,
            self.SPRITE_HEIGHT,
        )
        p.drawPixmap(dest, self._sprite_sheet, source)

        p.restore()
        p.end()
