from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QPointF, pyqtProperty
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from widgets.sprite_duck import SpriteDuck
import random
import math


class ModelWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._old_pos = None
        self._is_dragging = False
        self._swimming_enabled = True
        self._current_behavior = "idle"
        self._behavior_timer = None
        
        # Swimming path animation
        self._path_progress = 0.0
        self._path_start = None
        self._path_end = None
        self._path_control1 = None
        self._path_control2 = None
        self._path_timer = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setObjectName("quacky-model-window")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(SpriteDuck.SIZE, SpriteDuck.SIZE)

        self._build_ui()
        self._start_duck_life()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.quacky_widget = SpriteDuck()
        root.addWidget(self.quacky_widget)
    
    def _start_duck_life(self):
        """Start Quacky's autonomous duck behaviors"""
        QTimer.singleShot(1500, self._choose_next_behavior)
    
    def _choose_next_behavior(self):
        """Duck decides what to do next"""
        if self._is_dragging or not self._swimming_enabled:
            QTimer.singleShot(2000, self._choose_next_behavior)
            return
        
        # Duck behavior probabilities
        behaviors = [
            ("swim", 40),      # Swim around (most common)
            ("idle", 20),      # Just float and look around
            ("quick_swim", 15), # Quick dash across screen
            ("circle", 15),    # Swim in a circle
            ("explore", 10),   # Explore screen edges
        ]
        
        # Weighted random choice
        total = sum(weight for _, weight in behaviors)
        r = random.randint(1, total)
        cumulative = 0
        
        for behavior, weight in behaviors:
            cumulative += weight
            if r <= cumulative:
                self._current_behavior = behavior
                break
        
        # Execute the chosen behavior
        if self._current_behavior == "swim":
            self._swim_curved()
        elif self._current_behavior == "idle":
            self._idle_float()
        elif self._current_behavior == "quick_swim":
            self._quick_dash()
        elif self._current_behavior == "circle":
            self._swim_circle()
        elif self._current_behavior == "explore":
            self._explore_edges()
    
    def _swim_curved(self):
        """Swim in a smooth curved path (like a real duck)"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        
        screen_geo = screen.availableGeometry()
        margin = 80
        
        # Current position
        start = self.pos()
        
        # Random target
        target_x = random.randint(screen_geo.x() + margin, 
                                 screen_geo.x() + screen_geo.width() - self.width() - margin)
        target_y = random.randint(screen_geo.y() + margin,
                                 screen_geo.y() + screen_geo.height() - self.height() - margin)
        end = QPoint(target_x, target_y)
        
        # Create curved path with control points (Bezier curve)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        
        # Control points for natural curve
        control1_x = start.x() + dx * 0.3 + random.randint(-150, 150)
        control1_y = start.y() + dy * 0.3 + random.randint(-150, 150)
        control2_x = start.x() + dx * 0.7 + random.randint(-150, 150)
        control2_y = start.y() + dy * 0.7 + random.randint(-150, 150)
        
        self._path_start = start
        self._path_end = end
        self._path_control1 = QPointF(control1_x, control1_y)
        self._path_control2 = QPointF(control2_x, control2_y)
        
        # Animate along curve
        distance = math.sqrt(dx*dx + dy*dy)
        duration = int(min(6000, max(2500, distance * 6)))
        
        self._animate_along_path(duration)
    
    def _quick_dash(self):
        """Quick swim across screen (duck is excited!)"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        
        screen_geo = screen.availableGeometry()
        start = self.pos()
        
        # Pick a direction and swim far
        angle = random.uniform(0, 2 * math.pi)
        distance = random.randint(400, 800)
        
        target_x = start.x() + int(math.cos(angle) * distance)
        target_y = start.y() + int(math.sin(angle) * distance)
        
        # Clamp to screen
        margin = 50
        target_x = max(screen_geo.x() + margin, 
                      min(target_x, screen_geo.x() + screen_geo.width() - self.width() - margin))
        target_y = max(screen_geo.y() + margin,
                      min(target_y, screen_geo.y() + screen_geo.height() - self.height() - margin))
        
        # Set swimming direction for duck
        dx = target_x - start.x()
        dy = target_y - start.y()
        swim_angle = math.atan2(dy, dx)
        self.quacky_widget.set_swimming_direction(swim_angle)
        
        # Quick animation
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(1500)  # Fast!
        anim.setStartValue(start)
        anim.setEndValue(QPoint(target_x, target_y))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def on_finished():
            self.quacky_widget.set_swimming_direction(0.0)
            QTimer.singleShot(1000, self._choose_next_behavior)
        
        anim.finished.connect(on_finished)
        anim.start()
        self._path_timer = anim
    
    def _swim_circle(self):
        """Swim in a circular pattern"""
        center = self.pos()
        radius = random.randint(100, 200)
        
        # Animate in circle using path
        points = []
        steps = 20
        for i in range(steps + 1):
            angle = (i / steps) * 2 * math.pi
            x = center.x() + int(math.cos(angle) * radius)
            y = center.y() + int(math.sin(angle) * radius)
            points.append(QPoint(x, y))
        
        self._animate_through_points(points, 4000)
    
    def _explore_edges(self):
        """Swim along screen edges (curious duck)"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        
        screen_geo = screen.availableGeometry()
        margin = 60
        
        # Pick a random edge
        edge = random.choice(["top", "bottom", "left", "right"])
        
        if edge == "top":
            target_x = random.randint(screen_geo.x() + margin, 
                                     screen_geo.x() + screen_geo.width() - self.width() - margin)
            target_y = screen_geo.y() + margin
        elif edge == "bottom":
            target_x = random.randint(screen_geo.x() + margin,
                                     screen_geo.x() + screen_geo.width() - self.width() - margin)
            target_y = screen_geo.y() + screen_geo.height() - self.height() - margin
        elif edge == "left":
            target_x = screen_geo.x() + margin
            target_y = random.randint(screen_geo.y() + margin,
                                     screen_geo.y() + screen_geo.height() - self.height() - margin)
        else:  # right
            target_x = screen_geo.x() + screen_geo.width() - self.width() - margin
            target_y = random.randint(screen_geo.y() + margin,
                                     screen_geo.y() + screen_geo.height() - self.height() - margin)
        
        # Swim to edge with curve
        start = self.pos()
        end = QPoint(target_x, target_y)
        
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        
        self._path_start = start
        self._path_end = end
        self._path_control1 = QPointF(start.x() + dx * 0.4, start.y() + dy * 0.2)
        self._path_control2 = QPointF(start.x() + dx * 0.6, start.y() + dy * 0.8)
        
        self._animate_along_path(3500)
    
    def _idle_float(self):
        """Just float in place and look around"""
        # Duck stays put, just existing
        wait_time = random.randint(3000, 6000)
        QTimer.singleShot(wait_time, self._choose_next_behavior)
    
    def _animate_along_path(self, duration):
        """Animate along a Bezier curve path"""
        self._path_progress = 0.0
        
        if self._path_timer:
            self._path_timer.stop()
        
        self._path_timer = QTimer(self)
        self._path_timer.setInterval(16)  # ~60 FPS
        
        start_time = [0]  # Mutable to track in closure
        last_pos = [self.pos()]  # Track last position for direction
        
        def update_position():
            start_time[0] += 16
            progress = min(1.0, start_time[0] / duration)
            
            # Cubic Bezier curve calculation
            t = progress
            t2 = t * t
            t3 = t2 * t
            mt = 1 - t
            mt2 = mt * mt
            mt3 = mt2 * mt
            
            x = (mt3 * self._path_start.x() +
                 3 * mt2 * t * self._path_control1.x() +
                 3 * mt * t2 * self._path_control2.x() +
                 t3 * self._path_end.x())
            
            y = (mt3 * self._path_start.y() +
                 3 * mt2 * t * self._path_control1.y() +
                 3 * mt * t2 * self._path_control2.y() +
                 t3 * self._path_end.y())
            
            new_pos = QPoint(int(x), int(y))
            
            # Calculate swimming direction for duck animation
            dx = new_pos.x() - last_pos[0].x()
            dy = new_pos.y() - last_pos[0].y()
            if dx != 0 or dy != 0:
                angle = math.atan2(dy, dx)
                self.quacky_widget.set_swimming_direction(angle)
            
            self.move(new_pos)
            last_pos[0] = new_pos
            
            if progress >= 1.0:
                self._path_timer.stop()
                # Stop swimming animation
                self.quacky_widget.set_swimming_direction(0.0)
                wait = random.randint(1500, 4000)
                QTimer.singleShot(wait, self._choose_next_behavior)
        
        self._path_timer.timeout.connect(update_position)
        self._path_timer.start()
    
    def _animate_through_points(self, points, duration):
        """Animate through a series of points"""
        if not points:
            return
        
        current_point = [0]
        interval = duration // len(points)
        
        def move_to_next():
            if current_point[0] < len(points):
                self.move(points[current_point[0]])
                current_point[0] += 1
                QTimer.singleShot(interval, move_to_next)
            else:
                QTimer.singleShot(2000, self._choose_next_behavior)
        
        move_to_next()
    
    def stop_swimming(self):
        """Stop all duck behaviors"""
        self._swimming_enabled = False
        if self._path_timer:
            self._path_timer.stop()
    
    def start_swimming(self):
        """Resume duck behaviors"""
        self._swimming_enabled = True
        self._choose_next_behavior()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()
            self._is_dragging = True
            # Stop swimming while being held
            if self._path_timer:
                self._path_timer.stop()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._old_pos = None
        self._is_dragging = False
        # Duck resumes life after being released
        if self._swimming_enabled:
            QTimer.singleShot(2000, self._choose_next_behavior)
