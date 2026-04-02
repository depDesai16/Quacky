"""
Sprite-based duck animation widget using the Pixel Duck sprite sheet.
Replaces the hand-drawn duck with professional animated sprites.
"""
import math
from pathlib import Path
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPixmap, QTransform, QColor

class SpriteDuck(QWidget):
    """Animated duck using sprite sheet frames"""
    
    # Widget size
    W, H = 380, 440
    SIZE = 380
    
    # Animation settings
    FPS = 60
    
    # Sprite sheet layout - 480x544 image
    # 15 columns x 17 rows of 32x32 frames
    SPRITE_WIDTH = 32
    SPRITE_HEIGHT = 32
    COLS = 15  # 480 / 32 = 15 columns
    ROWS = 17  # 544 / 32 = 17 rows
    
    # Animation definitions (row_pair, start_col, num_frames, fps)
    # Each animation has 2 rows: even row = right-facing, odd row = left-facing
    ANIMATIONS = {
        'idle': (0, 0, 4, 6),           # Rows 0-1: 4 frames - standing/idle
        'jumping': (2, 0, 6, 10),       # Rows 2-3: 6 frames - jumping
        'sitting': (4, 0, 4, 6),        # Rows 4-5: 4 frames - sitting
        'eating': (6, 0, 4, 8),         # Rows 6-7: 4 frames - eating
        'sleeping': (8, 0, 4, 4),       # Rows 8,10: R=8, L=10 (row 9 is also right)
        'looking': (10, 0, 4, 6),       # Rows 10-11: 4 frames - looking around
        'flying': (11, 0, 10, 12),      # Rows 11-12: 10 frames - flying (for swimming!)
        'takeoff': (13, 0, 15, 12),     # Rows 13-14: 15 frames - taking off/landing
        'falling': (15, 0, 5, 8),       # Rows 15-16: 5 frames - falling
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Load sprite sheet
        sprite_path = Path(__file__).parent.parent / "animations" / "duck_spritesheet.png"
        self._sprite_sheet = QPixmap(str(sprite_path))
        
        if self._sprite_sheet.isNull():
            print(f"⚠️  Failed to load sprite sheet: {sprite_path}")
        else:
            print(f"✓ Loaded sprite sheet: {self._sprite_sheet.width()}x{self._sprite_sheet.height()}")
        
        # Animation state
        self._current_animation = 'idle'
        self._frame_index = 0
        self._frame_timer = 0
        self._t = 0
        
        # Position and movement
        self._x = self.W / 2
        self._y = self.H / 2
        self._float_offset = 0.0
        self._scale = 5.5  # Scale for 32x32 frames
        self._flip_h = False  # Use left-facing row instead of flipping
        
        # State
        self._state = "idle"  # idle, thinking, swimming
        self._thinking_bob = 0.0
        self._thinking_tilt = 0.0
        self._swim_rotation = 0.0
        self._swim_bob_offset = 0.0
        
        # Start animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000 // self.FPS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
    
    def set_animation(self, animation_name):
        """Change the current animation"""
        if animation_name in self.ANIMATIONS and animation_name != self._current_animation:
            self._current_animation = animation_name
            self._frame_index = 0
            self._frame_timer = 0
            anim = self.ANIMATIONS[animation_name]
            print(f"🦆 Animation: {animation_name} | Row: {anim[0]} | Frames: {anim[2]} | FPS: {anim[3]}")
    
    def set_state(self, state):
        """Set duck state (idle, thinking, swimming)"""
        self._state = state
        
        # Change animation based on state
        if state == "swimming":
            self.set_animation('flying')
        elif state == "thinking":
            self.set_animation('idle')
        else:
            self.set_animation('idle')
    
    def set_swimming_direction(self, angle):
        """Set swimming direction (in radians)"""
        if angle != 0:
            self.set_state("swimming")
            # Flip sprite based on direction
            degrees = math.degrees(angle)
            # Duck faces right by default, flip when moving left
            self._flip_h = degrees > 90 or degrees < -90
            self._swim_rotation = degrees * 0.15  # Very subtle tilt
    
    def start_thinking(self):
        """Start thinking animation"""
        self.set_state("thinking")
    
    def stop_thinking(self):
        """Stop thinking animation"""
        self.set_state("idle")
    
    def _tick(self):
        """Update animation frame"""
        dt = 1000 // self.FPS
        self._t += dt
        
        # Get current animation info
        anim = self.ANIMATIONS[self._current_animation]
        row, start_col, num_frames, anim_fps = anim
        
        # Update frame timer
        frame_duration = 1000 / anim_fps
        self._frame_timer += dt
        
        if self._frame_timer >= frame_duration:
            self._frame_timer = 0
            self._frame_index = (self._frame_index + 1) % num_frames
        
        # Update floating motion (slower, more gentle)
        if self._state in ("idle", "thinking"):
            self._float_offset = math.sin(self._t / 1000.0 * 2 * math.pi / 5.0) * 12.0
        
        # Update thinking animation
        if self._state == "thinking":
            self._thinking_bob = math.sin((self._t / 1000.0) * 2 * math.pi) * 25.0
            self._thinking_tilt = 0.0  # No tilt - causes spinning with sprites
        else:
            self._thinking_bob = 0.0
            self._thinking_tilt = 0.0
        
        # Update swimming bob
        if self._state == "swimming":
            self._swim_bob_offset = math.sin(self._t / 200.0 * 2 * math.pi) * 6.0
        else:
            self._swim_bob_offset = 0.0
            self._swim_rotation *= 0.92  # Smooth return to neutral
        
        self.update()
    
    def paintEvent(self, event):
        """Draw the animated sprite"""
        if self._sprite_sheet.isNull():
            # Fallback: draw a colored circle if sprite fails
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(255, 200, 0))
            painter.setPen(QColor(255, 150, 0))
            painter.drawEllipse(int(self._x - 30), int(self._y - 30), 60, 60)
            painter.end()
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # For pixel art, we want crisp pixels not blurry
        # But still smooth at larger scales
        
        # Get current frame from sprite sheet
        anim = self.ANIMATIONS[self._current_animation]
        base_row, start_col, num_frames, _ = anim
        
        col = start_col + self._frame_index
        
        # Calculate row based on facing direction
        # Most animations: right = base_row, left = base_row + 1
        # Exception: sleeping right=8, left=10 (row 9 is also right-facing)
        if self._flip_h:
            if base_row == 8:  # sleeping special case
                row = 10
            else:
                row = base_row + 1
        else:
            row = base_row
        
        # Extract frame from sprite sheet
        source_rect = QRectF(
            col * self.SPRITE_WIDTH,
            row * self.SPRITE_HEIGHT,
            self.SPRITE_WIDTH,
            self.SPRITE_HEIGHT
        )
        
        # Calculate position with all offsets
        y_pos = self._y + self._float_offset + self._thinking_bob + self._swim_bob_offset
        
        # Set up transformation
        painter.save()
        painter.translate(self._x, y_pos)
        
        # Apply rotations
        if self._state == "thinking":
            painter.rotate(self._thinking_tilt)
        if self._state == "swimming":
            painter.rotate(self._swim_rotation)
        
        # Apply scale (but NO flip - we use left/right rows instead)
        transform = QTransform()
        transform.scale(self._scale, self._scale)
        painter.setTransform(transform, True)
        
        # Draw sprite centered
        dest_rect = QRectF(
            -self.SPRITE_WIDTH / 2,
            -self.SPRITE_HEIGHT / 2,
            self.SPRITE_WIDTH,
            self.SPRITE_HEIGHT
        )
        
        painter.drawPixmap(dest_rect, self._sprite_sheet, source_rect)
        
        # Debug: Draw frame border
        if False:  # Set to True to see frame boundaries
            painter.setPen(QColor(255, 0, 0))
            painter.drawRect(dest_rect)
        
        painter.restore()
        painter.end()
