import math
import random
import threading
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (QPainter, QColor, QBrush, QPen, QPainterPath,
                          QRadialGradient, QIcon, QPixmap, QPainter, QColor)
from pathlib import Path

# Import Lottie widget
try:
    from .lottie_widget import LottieWidget
    LOTTIE_AVAILABLE = True
except ImportError:
    LOTTIE_AVAILABLE = False
    print("⚠️  Lottie widget not available")

## Public API

_pop_requested = threading.Event()
_reset_requested = threading.Event()
_thinking_requested = threading.Event()
_stop_thinking_requested = threading.Event()
_swimming_direction = 0.0  # Angle in radians for duck orientation

def pop_bubble():
    _pop_requested.set()

def reset_bubble():
    _reset_requested.set()

def start_thinking():
    _thinking_requested.set()

def stop_thinking():
    _stop_thinking_requested.set()

def set_swimming_direction(angle):
    """Set the direction the duck is swimming (in radians)"""
    global _swimming_direction
    _swimming_direction = angle

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
    SIZE = 380  # Add SIZE constant for ModelWindow
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
        
        # Thinking animation state
        self._thinking_bob = 0.0
        self._thinking_tilt = 0.0
        
        # Swimming animation state
        self._is_swimming = False
        self._swim_flap_speed = 2.5  # Much faster flapping when swimming
        self._swim_rotation = 0.0  # Duck body rotation to face direction
        self._swim_bob_offset = 0.0  # Extra bobbing when swimming
        self._paddle_phase = 0.0  # Foot paddling animation
        self._wake_ripples = []  # Water ripples behind duck
        
        # Lottie animation overlay
        self._lottie_widget = None
        if LOTTIE_AVAILABLE:
            try:
                anim_path = Path(__file__).parent.parent / "animations" / "duck_swim.json"
                if anim_path.exists():
                    self._lottie_widget = LottieWidget(str(anim_path), self)
                    self._lottie_widget.setGeometry(0, 0, self.W, self.H)
                    self._lottie_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    self._lottie_widget.hide()  # Hidden by default
                    print("✓ Lottie animation loaded")
                else:
                    print(f"⚠️  Animation file not found: {anim_path}")
            except Exception as e:
                print(f"⚠️  Failed to load Lottie animation: {e}")
                self._lottie_widget = None

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
        
        global _swimming_direction

        if _reset_requested.is_set():
            _reset_requested.clear()
            self._state = "idle"
            self._bubble_scale = 1.0
            self._bubble_alpha = 1.0
            self._duck_opacity = 1.0
            self._is_swimming = False

        if _thinking_requested.is_set() and self._state == "idle":
            _thinking_requested.clear()
            self._state = "thinking"
        
        if _stop_thinking_requested.is_set() and self._state == "thinking":
            _stop_thinking_requested.clear()
            self._state = "idle"

        if _pop_requested.is_set() and self._state == "idle":
            _pop_requested.clear()
            self._state = "popping"
            self._pop_ms = 0

        self._t += dt
        self._float_ms += dt if self._state in ("idle", "thinking") else 0

        self._tick_blink(dt)
        self._tick_gaze(dt)
        
        if self._state == "thinking":
            self._tick_thinking(dt)
        
        # Check if swimming (direction changed recently)
        if _swimming_direction != 0.0:
            self._is_swimming = True
            # Smoothly rotate duck to face swimming direction
            target_rotation = math.degrees(_swimming_direction)
            self._swim_rotation += (target_rotation - self._swim_rotation) * 0.15
            
            # Add swimming bob (up and down motion)
            self._swim_bob_offset = math.sin(self._t / 200.0 * 2 * math.pi) * 6.0
            
            # Paddle animation
            self._paddle_phase = (self._t / 300.0) % (2 * math.pi)
            
            # Add wake ripples
            if self._t % 200 < 20:  # Every 200ms
                self._wake_ripples.append({
                    'x': self.BX,
                    'y': self.BY,
                    'age': 0,
                    'max_age': 1000
                })
            
            # Show Lottie animation when swimming
            if self._lottie_widget and not self._lottie_widget.isVisible():
                self._lottie_widget.show()
                self._lottie_widget.play()
                print("🦆 Swimming animation started")
        else:
            self._is_swimming = False
            # Return to neutral rotation
            self._swim_rotation *= 0.92
            self._swim_bob_offset *= 0.9
            
            # Hide Lottie animation when not swimming
            if self._lottie_widget and self._lottie_widget.isVisible():
                self._lottie_widget.pause()
                self._lottie_widget.hide()
                print("🦆 Swimming animation stopped")
        
        # Update wake ripples
        self._wake_ripples = [r for r in self._wake_ripples if r['age'] < r['max_age']]
        for ripple in self._wake_ripples:
            ripple['age'] += dt

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
    
    def _tick_thinking(self, dt):
        """Animate thinking state - bob and tilt"""
        # Bob up and down MORE (1000ms cycle, 20 pixels)
        self._thinking_bob = math.sin((self._t / 1000.0) * 2 * math.pi) * 20.0
        
        # Tilt head left and right MORE (1400ms cycle, 15 degrees)
        self._thinking_tilt = math.sin((self._t / 1400.0) * 2 * math.pi) * 15.0

    def _flap(self):
        # Faster flapping when swimming
        speed_multiplier = self._swim_flap_speed if self._is_swimming else 1.0
        period = self.FLAP_PERIOD / speed_multiplier
        flap_value = math.sin((self._t / period) * 2 * math.pi) * 16
        
        # Much bigger flaps when swimming
        if self._is_swimming:
            flap_value *= 3.0  # 3x bigger wing movement
        
        return flap_value

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

        # Apply thinking animation offset
        thinking_offset = self._thinking_bob if self._state == "thinking" else 0.0
        
        # Apply swimming bob
        swim_bob = self._swim_bob_offset if self._is_swimming else 0.0
        
        dy = (math.sin(self._float_ms / 1000.0 * 2 * math.pi / self.FLOAT_FREQ)
              * self.FLOAT_AMP if self._state in ("idle", "thinking") else 0.0)
        cy = self.BY + dy + thinking_offset + swim_bob
        br = self.BR * self._bubble_scale

        # Draw wake ripples behind duck when swimming
        if self._is_swimming:
            self._draw_wake_ripples(p)

        self._draw_glow(p, self.BX, cy, self.BR)

        p.setOpacity(self._bubble_alpha)
        self._draw_bubble(p, self.BX, cy, br)

        p.setOpacity(self._duck_opacity)
        
        # Apply swimming rotation to entire duck
        if self._is_swimming or abs(self._swim_rotation) > 0.5:
            p.save()
            p.translate(self.BX, cy)
            p.rotate(self._swim_rotation * 0.4)  # More noticeable tilt
            p.translate(-self.BX, -cy)
        
        # Apply thinking tilt to duck
        if self._state == "thinking":
            p.save()
            p.translate(self.BX, cy)
            p.rotate(self._thinking_tilt)
            p.translate(-self.BX, -cy)
        
        # Draw duck with enhanced flapping
        flap_amount = self._flap()
        
        self._draw_duck(p, self.BX, cy, flap_amount, self._blink_scale(), self._gaze_x, self._gaze_y, self._is_swimming)
        
        # Draw paddling feet when swimming
        if self._is_swimming:
            self._draw_paddling_feet(p, self.BX, cy)
        
        if self._state == "thinking":
            p.restore()
        
        if self._is_swimming or abs(self._swim_rotation) > 0.5:
            p.restore()

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
    def _draw_duck(p, cx, cy, flap=0.0, bs=1.0, gaze_x=0.0, gaze_y=0.0, is_swimming=False):
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

        # Belly / Wing - much more dramatic flapping
        # Base multiplier increased from 0.28 to 1.2 for visible wing movement
        # Even more dramatic when swimming (2.5x)
        wing_multiplier = 2.5 if is_swimming else 1.2
        belly_rock = flap * wing_multiplier
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

    def _draw_wake_ripples(self, p):
        """Draw water ripples behind swimming duck"""
        p.setPen(Qt.PenStyle.NoPen)
        for ripple in self._wake_ripples:
            progress = ripple['age'] / ripple['max_age']
            radius = 20 + progress * 40
            alpha = int(80 * (1 - progress))
            
            color = QColor(150, 200, 255, alpha)
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(ripple['x'], ripple['y']), radius, radius * 0.6)
    
    def _draw_paddling_feet(self, p, cx, cy):
        """Draw animated paddling feet under the duck"""
        # Feet are under the duck body
        foot_y = cy + 35
        
        # Left foot
        left_offset = math.sin(self._paddle_phase) * 8
        left_x = cx - 15 + left_offset
        self._draw_foot(p, left_x, foot_y, left_offset)
        
        # Right foot (opposite phase)
        right_offset = math.sin(self._paddle_phase + math.pi) * 8
        right_x = cx + 15 + right_offset
        self._draw_foot(p, right_x, foot_y, right_offset)
    
    def _draw_foot(self, p, x, y, offset):
        """Draw a single webbed foot"""
        # Foot color
        foot_color = QColor(255, 180, 40, 180)
        p.setBrush(QBrush(foot_color))
        p.setPen(QPen(QColor(220, 140, 20, 150), 1))
        
        # Webbed foot shape (simple oval)
        foot_width = 12 + abs(offset) * 0.5  # Wider when extended
        foot_height = 8
        p.drawEllipse(QPointF(x, y), foot_width, foot_height)

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