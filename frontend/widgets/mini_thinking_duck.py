"""
mini_thinking_duck.py - Small animated duck for thinking state
"""

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer
from PyQt6.QtGui import QPainter, QPixmap, QTransform
from PyQt6.QtWidgets import QWidget, QSizePolicy


class MiniThinkingDuck(QWidget):
    """Small animated duck that bobs up and down while thinking"""
    
    def __init__(self, icon_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._icon = icon_pixmap
        self._offset_y = 0.0
        self._rotation = 0.0
        
        # Size for mini duck (smaller than main)
        self._size = 24
        self.setFixedSize(self._size + 4, self._size + 8)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Start animations
        self._start_bob_animation()
        self._start_rotation_animation()
    
    def _get_offset_y(self) -> float:
        return self._offset_y
    
    def _set_offset_y(self, v: float):
        self._offset_y = v
        self.update()
    
    offset_y = pyqtProperty(float, _get_offset_y, _set_offset_y)
    
    def _get_rotation(self) -> float:
        return self._rotation
    
    def _set_rotation(self, v: float):
        self._rotation = v
        self.update()
    
    rotation = pyqtProperty(float, _get_rotation, _set_rotation)
    
    def _start_bob_animation(self):
        """Animate vertical bobbing motion"""
        self._bob_anim = QPropertyAnimation(self, b"offset_y", self)
        self._bob_anim.setDuration(800)
        self._bob_anim.setStartValue(0.0)
        self._bob_anim.setKeyValueAt(0.5, -4.0)  # Bob up 4 pixels
        self._bob_anim.setEndValue(0.0)
        self._bob_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._bob_anim.setLoopCount(-1)
        self._bob_anim.start()
    
    def _start_rotation_animation(self):
        """Animate subtle rotation (thinking head tilt)"""
        self._rot_anim = QPropertyAnimation(self, b"rotation", self)
        self._rot_anim.setDuration(1200)
        self._rot_anim.setStartValue(-5.0)
        self._rot_anim.setKeyValueAt(0.5, 5.0)
        self._rot_anim.setEndValue(-5.0)
        self._rot_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._rot_anim.setLoopCount(-1)
        # Stagger the rotation slightly
        QTimer.singleShot(200, self._rot_anim.start)
    
    def stop_animations(self):
        """Stop all animations"""
        if hasattr(self, '_bob_anim'):
            self._bob_anim.stop()
        if hasattr(self, '_rot_anim'):
            self._rot_anim.stop()
    
    def paintEvent(self, event):
        """Paint the mini duck with animations"""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Calculate center position with offset
        cx = self.width() / 2
        cy = (self.height() / 2) + self._offset_y
        
        # Apply rotation transform
        transform = QTransform()
        transform.translate(cx, cy)
        transform.rotate(self._rotation)
        transform.translate(-self._size / 2, -self._size / 2)
        p.setTransform(transform)
        
        # Draw the duck icon scaled down
        scaled_icon = self._icon.scaled(
            self._size, self._size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        p.drawPixmap(0, 0, scaled_icon)
        
        p.end()
    
    def __del__(self):
        try:
            self.stop_animations()
        except Exception:
            pass
