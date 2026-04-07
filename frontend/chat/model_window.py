from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from widgets.sprite_duck import SpriteDuck
import random
import math


class ModelWindow(QWidget):
    clicked = pyqtSignal()  # Emitted when duck is clicked (not dragged)
    file_dropped = pyqtSignal(str)  # Emitted when a file is dropped on the duck
    def __init__(self):
        super().__init__()
        self._old_pos = None
        self._is_dragging = False
        self._move_timer = None
        self._wait_timer = None
        self._gen = 0  # generation counter to invalidate stale callbacks

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setObjectName("quacky-model-window")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(SpriteDuck.SIZE, SpriteDuck.SIZE)

        self._build_ui()
        self.setAcceptDrops(True)
        self._schedule_next(1500)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.quacky_widget = SpriteDuck()
        root.addWidget(self.quacky_widget)

    def _cancel_all(self):
        """Stop all timers and bump generation so stale callbacks are ignored."""
        self._gen += 1
        if self._move_timer is not None:
            self._move_timer.stop()
            self._move_timer.deleteLater()
            self._move_timer = None
        if self._wait_timer is not None:
            self._wait_timer.stop()
            self._wait_timer.deleteLater()
            self._wait_timer = None

    def _schedule_next(self, delay_ms):
        """Schedule _next after a delay, cancellable."""
        gen = self._gen
        self._wait_timer = QTimer(self)
        self._wait_timer.setSingleShot(True)
        self._wait_timer.timeout.connect(lambda: self._next(gen))
        self._wait_timer.start(delay_ms)

    def _next(self, gen=None):
        """Pick next behavior. Ignores call if generation has changed."""
        if gen is not None and gen != self._gen:
            return
        if self._is_dragging:
            return

        self._cancel_all()

        roll = random.randint(1, 100)
        if roll <= 45:
            self._do_fly()
        elif roll <= 65:
            self._do_sit()
        elif roll <= 80:
            self._do_idle()
        else:
            self._do_follow_mouse()

    # ── Fly ──────────────────────────────────────────────

    def _do_fly(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return

        geo = screen.availableGeometry()
        margin = 80
        start = self.pos()

        tx = random.randint(geo.x() + margin, geo.x() + geo.width() - self.width() - margin)
        ty = random.randint(geo.y() + margin, geo.y() + geo.height() - self.height() - margin)

        dx = tx - start.x()
        dy = ty - start.y()
        c1 = QPointF(start.x() + dx * 0.3 + random.randint(-60, 60),
                      start.y() + dy * 0.3 + random.randint(-60, 60))
        c2 = QPointF(start.x() + dx * 0.7 + random.randint(-60, 60),
                      start.y() + dy * 0.7 + random.randint(-60, 60))
        end = QPointF(tx, ty)
        p0 = QPointF(start.x(), start.y())

        distance = math.sqrt(dx * dx + dy * dy)
        duration = int(min(5000, max(2000, distance * 5)))

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
            x = mt**3*p0.x() + 3*mt**2*t*c1.x() + 3*mt*t**2*c2.x() + t**3*end.x()
            y = mt**3*p0.y() + 3*mt**2*t*c1.y() + 3*mt*t**2*c2.y() + t**3*end.y()

            new_pos = QPoint(int(x), int(y))
            ddx = new_pos.x() - last[0].x()
            ddy = new_pos.y() - last[0].y()

            # Update facing direction only on significant horizontal movement
            if abs(ddx) > 2:
                self.quacky_widget._flip_h = ddx < 0

            # Keep flying animation active (don't call set_swimming_direction
            # every frame - that causes toggling)
            if self.quacky_widget._current_animation != 'flying':
                self.quacky_widget.set_animation('flying')
                self.quacky_widget._state = "swimming"

            self.move(new_pos)
            last[0] = new_pos

            if t >= 1.0:
                self._cancel_all()
                self.quacky_widget.set_swimming_direction(0.0)
                self._schedule_next(random.randint(1500, 3500))

        self._move_timer.timeout.connect(step)
        self._move_timer.start()

    # ── Sit ──────────────────────────────────────────────

    def _do_sit(self):
        self.quacky_widget.set_swimming_direction(0.0)
        self.quacky_widget.set_animation('sitting')
        self._schedule_next(random.randint(4000, 7000))

    # ── Idle ─────────────────────────────────────────────

    def _do_idle(self):
        self.quacky_widget.set_swimming_direction(0.0)
        self.quacky_widget.set_animation('idle')
        self._schedule_next(random.randint(2000, 4000))

    # ── Follow Mouse ───────────────────────────────────

    def _do_follow_mouse(self):
        """Chase the mouse cursor for a few seconds."""
        gen = self._gen
        follow_duration = random.randint(4000, 7000)
        elapsed = [0]

        self._move_timer = QTimer(self)
        self._move_timer.setInterval(50)  # Update 20x/sec

        def step():
            if gen != self._gen or self._is_dragging:
                return

            elapsed[0] += 50
            if elapsed[0] >= follow_duration:
                self._cancel_all()
                self.quacky_widget.set_swimming_direction(0.0)
                self._schedule_next(random.randint(1500, 3000))
                return

            cursor = self.cursor().pos()
            cx = cursor.x() - self.width() // 2
            cy = cursor.y() - self.height() // 2
            cur = self.pos()

            dx = cx - cur.x()
            dy = cy - cur.y()
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < 30:
                # Close enough, just idle near cursor
                if self.quacky_widget._current_animation != 'idle':
                    self.quacky_widget.set_swimming_direction(0.0)
                return

            # Move toward cursor at a steady pace
            speed = min(8, dist * 0.05)
            nx = cur.x() + int(dx / dist * speed)
            ny = cur.y() + int(dy / dist * speed)

            if abs(dx) > 2:
                self.quacky_widget._flip_h = dx < 0
            if self.quacky_widget._current_animation != 'flying':
                self.quacky_widget.set_animation('flying')
                self.quacky_widget._state = "swimming"

            self.move(nx, ny)

        self._move_timer.timeout.connect(step)
        self._move_timer.start()

    # ── Reactions to Quacky chat ────────────────────────

    def react_to_question(self, chat_window_pos):
        """Duck flies toward the chat window and starts thinking."""
        self._cancel_all()

        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()

        # Pick the side with more space
        space_left = chat_window_pos.x() - geo.x()
        space_right = (geo.x() + geo.width()) - (chat_window_pos.x() + 400)

        if space_right >= self.width():
            target_x = chat_window_pos.x() + 400 + 10
        elif space_left >= self.width():
            target_x = chat_window_pos.x() - self.width() - 10
        else:
            target_x = chat_window_pos.x() + 400 + 10

        # Clamp to screen
        target_x = max(geo.x(), min(target_x, geo.x() + geo.width() - self.width()))
        target_y = max(geo.y(), min(chat_window_pos.y() + 60, geo.y() + geo.height() - self.height()))

        start = self.pos()
        dx = target_x - start.x()
        dy = target_y - start.y()

        if abs(dx) > 5 or abs(dy) > 5:
            self.quacky_widget.set_swimming_direction(math.atan2(dy, dx))

        p0 = QPointF(start.x(), start.y())
        end = QPointF(target_x, target_y)
        c1 = QPointF(start.x() + dx * 0.4, start.y() + dy * 0.2)
        c2 = QPointF(start.x() + dx * 0.6, start.y() + dy * 0.8)

        distance = math.sqrt(dx * dx + dy * dy)
        duration = int(min(2000, max(800, distance * 3)))

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
            x = mt**3*p0.x() + 3*mt**2*t*c1.x() + 3*mt*t**2*c2.x() + t**3*end.x()
            y = mt**3*p0.y() + 3*mt**2*t*c1.y() + 3*mt*t**2*c2.y() + t**3*end.y()

            new_pos = QPoint(int(x), int(y))
            ddx = new_pos.x() - last[0].x()
            if abs(ddx) > 2:
                self.quacky_widget._flip_h = ddx < 0

            if self.quacky_widget._current_animation != 'flying':
                self.quacky_widget.set_animation('flying')
                self.quacky_widget._state = "swimming"

            self.move(new_pos)
            last[0] = new_pos

            if t >= 1.0:
                self._cancel_all()
                self.quacky_widget.set_swimming_direction(0.0)
                self.quacky_widget.start_thinking()

        self._move_timer.timeout.connect(step)
        self._move_timer.start()

    def react_to_response(self):
        """Duck stops thinking and resumes normal behavior."""
        self._cancel_all()
        self.quacky_widget.stop_thinking()
        self._schedule_next(2000)

    # ── Drag ─────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()
            self._drag_started = False
            self._is_dragging = True
            self._cancel_all()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._drag_started = True
            if self._drag_started:
                self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if not self._drag_started:
            self.clicked.emit()
        self._old_pos = None
        self._is_dragging = False
        self._drag_started = False
        self._schedule_next(1500)

    # ── File Drop ────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Duck gets excited - show sitting (alert) animation
            self._cancel_all()
            self.quacky_widget.set_animation('sitting')

    def dragLeaveEvent(self, event):
        self._schedule_next(500)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path:
                self.file_dropped.emit(file_path)
                self._cancel_all()
                self.quacky_widget.set_animation('idle')
                self._schedule_next(2000)
