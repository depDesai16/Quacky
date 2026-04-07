"""
lottie_widget.py - Lottie animation player for PyQt6
"""
import json
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import QWidget
from pathlib import Path


class LottieWidget(QWidget):
    """Widget that plays Lottie animations"""
    
    def __init__(self, animation_path, parent=None):
        super().__init__(parent)
        self.animation_data = None
        self.current_frame = 0
        self.total_frames = 0
        self.frame_rate = 60
        self.is_playing = False
        self.loop = True
        
        # Load animation
        self.load_animation(animation_path)
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_frame)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def load_animation(self, path):
        """Load Lottie JSON animation"""
        try:
            animation_file = Path(path)
            if animation_file.exists():
                with open(animation_file, 'r') as f:
                    self.animation_data = json.load(f)
                    self.total_frames = self.animation_data.get('op', 60)
                    self.frame_rate = self.animation_data.get('fr', 60)
                    print(f"✓ Loaded Lottie animation: {self.total_frames} frames @ {self.frame_rate}fps")
            else:
                print(f"✗ Animation file not found: {path}")
        except Exception as e:
            print(f"✗ Failed to load animation: {e}")
    
    def play(self):
        """Start playing the animation"""
        if not self.is_playing and self.animation_data:
            self.is_playing = True
            interval = int(1000 / self.frame_rate)
            self.timer.start(interval)
    
    def pause(self):
        """Pause the animation"""
        self.is_playing = False
        self.timer.stop()
    
    def stop(self):
        """Stop and reset the animation"""
        self.pause()
        self.current_frame = 0
        self.update()
    
    def _advance_frame(self):
        """Move to next frame"""
        self.current_frame += 1
        if self.current_frame >= self.total_frames:
            if self.loop:
                self.current_frame = 0
            else:
                self.pause()
        self.update()
    
    def paintEvent(self, event):
        """Render the current frame"""
        if not self.animation_data:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get animation dimensions
        anim_width = self.animation_data.get('w', 400)
        anim_height = self.animation_data.get('h', 400)
        
        # Scale to widget size
        scale_x = self.width() / anim_width
        scale_y = self.height() / anim_height
        scale = min(scale_x, scale_y)
        
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(scale, scale)
        painter.translate(-anim_width / 2, -anim_height / 2)
        
        # Render layers
        layers = self.animation_data.get('layers', [])
        for layer in layers:
            self._render_layer(painter, layer)
        
        painter.end()
    
    def _render_layer(self, painter, layer):
        """Render a single layer"""
        if layer.get('ty') != 4:  # Only shape layers for now
            return
        
        # Get transform properties
        transform = layer.get('ks', {})
        position = self._get_animated_value(transform.get('p'), self.current_frame)
        rotation = self._get_animated_value(transform.get('r'), self.current_frame)
        opacity = self._get_animated_value(transform.get('o'), self.current_frame)
        
        painter.save()
        
        # Apply transforms
        if position:
            # Handle both list and single values
            if isinstance(position, list) and len(position) >= 2:
                painter.translate(position[0], position[1])
        
        if rotation is not None:
            # Handle both list and single values
            if isinstance(rotation, list):
                rotation = rotation[0] if len(rotation) > 0 else 0
            painter.rotate(float(rotation))
        
        # Set opacity
        if opacity is not None:
            if isinstance(opacity, list):
                opacity = opacity[0] if len(opacity) > 0 else 100
            painter.setOpacity(float(opacity) / 100.0)
        
        # Render shapes
        shapes = layer.get('shapes', [])
        for shape in shapes:
            self._render_shape(painter, shape)
        
        painter.restore()
    
    def _render_shape(self, painter, shape):
        """Render a shape group"""
        if shape.get('ty') == 'gr':  # Group
            items = shape.get('it', [])
            
            # Find fill and stroke
            fill_color = None
            stroke_color = None
            ellipse_data = None
            
            for item in items:
                if item.get('ty') == 'fl':  # Fill
                    color_data = item.get('c', {}).get('k', [1, 1, 1, 1])
                    fill_color = QColor(
                        int(color_data[0] * 255),
                        int(color_data[1] * 255),
                        int(color_data[2] * 255),
                        int(color_data[3] * 255) if len(color_data) > 3 else 255
                    )
                elif item.get('ty') == 'st':  # Stroke
                    color_data = item.get('c', {}).get('k', [0, 0, 0, 1])
                    stroke_color = QColor(
                        int(color_data[0] * 255),
                        int(color_data[1] * 255),
                        int(color_data[2] * 255),
                        int(color_data[3] * 255) if len(color_data) > 3 else 255
                    )
                elif item.get('ty') == 'el':  # Ellipse
                    ellipse_data = item
            
            # Draw ellipse if found
            if ellipse_data:
                pos = ellipse_data.get('p', {}).get('k', [0, 0])
                size = ellipse_data.get('s', {}).get('k', [100, 100])
                
                if fill_color:
                    painter.setBrush(QBrush(fill_color))
                else:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                
                if stroke_color:
                    painter.setPen(QPen(stroke_color, 2))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                
                painter.drawEllipse(
                    QRectF(
                        pos[0] - size[0] / 2,
                        pos[1] - size[1] / 2,
                        size[0],
                        size[1]
                    )
                )
    
    def _get_animated_value(self, prop, frame):
        """Get interpolated value for current frame"""
        if not prop:
            return None
        
        # Static value
        if prop.get('a') == 0:
            return prop.get('k')
        
        # Animated value
        keyframes = prop.get('k', [])
        if not keyframes:
            return None
        
        # Find surrounding keyframes
        for i, kf in enumerate(keyframes):
            if kf.get('t', 0) > frame:
                if i == 0:
                    return kf.get('s')
                
                # Interpolate between previous and current keyframe
                prev_kf = keyframes[i - 1]
                t1 = prev_kf.get('t', 0)
                t2 = kf.get('t', 0)
                v1 = prev_kf.get('s')
                v2 = kf.get('s')
                
                if t2 == t1:
                    return v1
                
                # Linear interpolation
                progress = (frame - t1) / (t2 - t1)
                
                if isinstance(v1, list):
                    return [v1[j] + (v2[j] - v1[j]) * progress for j in range(len(v1))]
                else:
                    return v1 + (v2 - v1) * progress
        
        # Return last keyframe value
        return keyframes[-1].get('s')
