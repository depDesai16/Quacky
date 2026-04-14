import math
import random

from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget

from widgets.sprite_duck import SpriteDuck


class ModelWindow(QWidget):
    def __init__(self):
        """Initialize the instance state."""
        super().__init__()
        self._old_pos = None
        self._drag_started = False
        self._is_dragging = False
        self._using_system_move = False
        self._move_timer = None
        self._wait_timer = None
        self._gen = 0
        app = QApplication.instance()
        platform_name = (
            app.platformName().lower()
            if app is not None and hasattr(app, "platformName")
            else ""
        )
        self._programmatic_move_allowed = "wayland" not in platform_name

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setObjectName("quacky-model-window")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(SpriteDuck.W, SpriteDuck.H)

        self._build_ui()
        self._schedule_next(1200)

    def _build_ui(self):
        """Build ui."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.quacky_widget = SpriteDuck()
        root.addWidget(self.quacky_widget)

    def _cancel_all(self):
        """Stop all active timers and invalidate stale callbacks."""
        self._gen += 1
        if self._move_timer is not None:
            self._move_timer.stop()
            self._move_timer.deleteLater()
            self._move_timer = None
        if self._wait_timer is not None:
            self._wait_timer.stop()
            self._wait_timer.deleteLater()
            self._wait_timer = None

    def _schedule_next(self, delay_ms: int):
        """Schedule the next autonomous behavior."""
        gen = self._gen
        self._wait_timer = QTimer(self)
        self._wait_timer.setSingleShot(True)
        self._wait_timer.timeout.connect(lambda: self._next(gen))
        self._wait_timer.start(delay_ms)

    def _next(self, gen: int | None = None):
        """Pick the next behavior cycle."""
        if gen is not None and gen != self._gen:
            return
        if self._is_dragging:
            return
        if not self._programmatic_move_allowed:
            self._do_idle()
            return

        self._cancel_all()
        roll = random.randint(1, 100)
        if roll <= 55:
            self._do_fly()
        elif roll <= 80:
            self._do_idle()
        else:
            self._do_follow_mouse()

    def _do_idle(self):
        """Play idle animation briefly."""
        self.quacky_widget.set_swimming_direction(0.0)
        self.quacky_widget.set_animation("idle")
        self._schedule_next(random.randint(1400, 2600))

    def _do_fly(self):
        """Fly to a random position on screen using a bezier arc."""
        if not self._programmatic_move_allowed:
            self._do_idle()
            return

        screen = QApplication.primaryScreen()
        if not screen:
            self._schedule_next(1000)
            return

        geo = screen.availableGeometry()
        margin = 80
        start = self.pos()

        max_x = max(geo.x() + margin, geo.x() + geo.width() - self.width() - margin)
        max_y = max(geo.y() + margin, geo.y() + geo.height() - self.height() - margin)
        tx = random.randint(geo.x() + margin, max_x)
        ty = random.randint(geo.y() + margin, max_y)

        dx = tx - start.x()
        dy = ty - start.y()
        c1 = QPointF(
            start.x() + dx * 0.3 + random.randint(-60, 60),
            start.y() + dy * 0.3 + random.randint(-60, 60),
        )
        c2 = QPointF(
            start.x() + dx * 0.7 + random.randint(-60, 60),
            start.y() + dy * 0.7 + random.randint(-60, 60),
        )
        end = QPointF(tx, ty)
        p0 = QPointF(start.x(), start.y())

        distance = math.sqrt(dx * dx + dy * dy)
        duration = int(min(4200, max(1200, distance * 4.2)))

        self.quacky_widget.set_swimming_direction(math.atan2(dy, dx))

        elapsed = [0]
        last = [start]
        gen = self._gen

        self._move_timer = QTimer(self)
        self._move_timer.setInterval(16)

        def step():
            if gen != self._gen or self._is_dragging:
                return
            elapsed[0] += 16
            t = min(1.0, elapsed[0] / duration)
            mt = 1 - t
            x = mt**3 * p0.x() + 3 * mt**2 * t * c1.x() + 3 * mt * t**2 * c2.x() + t**3 * end.x()
            y = mt**3 * p0.y() + 3 * mt**2 * t * c1.y() + 3 * mt * t**2 * c2.y() + t**3 * end.y()

            new_pos = QPoint(int(x), int(y))
            ddx = new_pos.x() - last[0].x()
            if abs(ddx) > 2:
                self.quacky_widget._flip_h = ddx < 0

            if self.quacky_widget._current_animation != "flying":
                self.quacky_widget.set_animation("flying")
                self.quacky_widget._state = "swimming"

            self.move(new_pos)
            last[0] = new_pos

            if t >= 1.0:
                self._cancel_all()
                self.quacky_widget.set_swimming_direction(0.0)
                self._schedule_next(random.randint(1000, 2200))

        self._move_timer.timeout.connect(step)
        self._move_timer.start()

    def _do_follow_mouse(self):
        """Briefly chase the mouse cursor."""
        if not self._programmatic_move_allowed:
            self._do_idle()
            return

        gen = self._gen
        follow_duration = random.randint(2200, 4200)
        elapsed = [0]

        self._move_timer = QTimer(self)
        self._move_timer.setInterval(50)

        def step():
            if gen != self._gen or self._is_dragging:
                return

            elapsed[0] += 50
            if elapsed[0] >= follow_duration:
                self._cancel_all()
                self.quacky_widget.set_swimming_direction(0.0)
                self._schedule_next(random.randint(900, 1800))
                return

            cursor = self.cursor().pos()
            cx = cursor.x() - self.width() // 2
            cy = cursor.y() - self.height() // 2
            cur = self.pos()

            dx = cx - cur.x()
            dy = cy - cur.y()
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 30:
                self.quacky_widget.set_swimming_direction(0.0)
                return

            speed = min(9, dist * 0.06)
            nx = cur.x() + int(dx / dist * speed)
            ny = cur.y() + int(dy / dist * speed)

            if abs(dx) > 2:
                self.quacky_widget._flip_h = dx < 0
            if self.quacky_widget._current_animation != "flying":
                self.quacky_widget.set_animation("flying")
                self.quacky_widget._state = "swimming"

            self.move(nx, ny)

        self._move_timer.timeout.connect(step)
        self._move_timer.start()

    def _window_handle(self):
        """Return native window handle if available."""
        handle = self.windowHandle()
        if handle is None:
            self.winId()
            handle = self.windowHandle()
        return handle

    def _start_system_move(self) -> bool:
        """Use native compositor drag when available."""
        handle = self._window_handle()
        if handle is None or not hasattr(handle, "startSystemMove"):
            return False
        try:
            return bool(handle.startSystemMove())
        except Exception:
            return False

    def mousePressEvent(self, event):
        """Handle mousepress event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()
            self._drag_started = False
            self._is_dragging = True
            self._cancel_all()
            if self._start_system_move():
                self._using_system_move = True
                self._old_pos = None
                self._drag_started = True
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mousemove event."""
        if self._using_system_move:
            super().mouseMoveEvent(event)
            return
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._drag_started = True
            if self._drag_started:
                self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouserelease event."""
        self._using_system_move = False
        self._old_pos = None
        self._is_dragging = False
        self._drag_started = False
        self._schedule_next(900)
        super().mouseReleaseEvent(event)
