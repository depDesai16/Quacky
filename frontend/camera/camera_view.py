"""
camera_view.py - Camera view widget with face tracking and analysis
"""
import cv2
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QImage, QPixmap, QFont
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import ThemeManager
from .camera_analyzer import CameraAnalyzer


class CameraThread(QThread):
    """Thread for capturing and analyzing camera frames"""
    frame_ready = pyqtSignal(object, dict)  # frame, analysis_results
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
        self.analyzer = CameraAnalyzer()
    
    def run(self):
        self.cap = cv2.VideoCapture(0)
        self.running = True
        
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Analyze frame
                results = self.analyzer.analyze_frame(frame)
                
                # Emit frame and analysis results
                self.frame_ready.emit(frame, results)
            
            self.msleep(33)  # ~30 FPS
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.analyzer.cleanup()


class CameraView(QWidget):
    """Camera view widget with face tracking and analysis"""
    
    # Signals for detected features
    emotion_detected = pyqtSignal(str, float)
    gesture_detected = pyqtSignal(str)
    attention_changed = pyqtSignal(bool)
    user_recognized = pyqtSignal(str, float)  # Add user recognition signal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens = ThemeManager.tokens()
        self.camera_thread = None
        self.current_frame = None
        self.current_results = {}
        
        self._build_ui()
        ThemeManager.subscribe(self._on_theme)
    
    def _build_ui(self):
        """Build the camera view UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Camera display label
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        
        # Status display
        self.status_widget = self._create_status_widget()
        
        layout.addWidget(self.camera_label, 1)
        layout.addWidget(self.status_widget)
        
        self._apply_theme()
    
    def _create_status_widget(self):
        """Create widget to display detection status"""
        from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QLineEdit
        
        status_container = QWidget()
        main_layout = QVBoxLayout(status_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)
        
        # Status row
        status_row = QWidget()
        status_layout = QHBoxLayout(status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(16)
        
        # User label
        self.user_label = QLabel("👤 Guest")
        self.user_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        
        # Emotion label
        self.emotion_label = QLabel("😐 Neutral")
        self.emotion_label.setFont(QFont("Segoe UI", 12))
        
        # Gesture label
        self.gesture_label = QLabel("👋 No gesture")
        self.gesture_label.setFont(QFont("Segoe UI", 12))
        
        # Attention label
        self.attention_label = QLabel("👀 Attentive")
        self.attention_label.setFont(QFont("Segoe UI", 12))
        
        status_layout.addWidget(self.user_label)
        status_layout.addWidget(self.emotion_label)
        status_layout.addWidget(self.gesture_label)
        status_layout.addWidget(self.attention_label)
        status_layout.addStretch()
        
        # Registration row
        register_row = QWidget()
        register_layout = QHBoxLayout(register_row)
        register_layout.setContentsMargins(0, 0, 0, 0)
        register_layout.setSpacing(8)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name to register...")
        self.name_input.setMaximumWidth(250)
        
        self.register_btn = QPushButton("📸 Register Face")
        self.register_btn.clicked.connect(self._on_register_user)
        
        register_layout.addWidget(self.name_input)
        register_layout.addWidget(self.register_btn)
        register_layout.addStretch()
        
        main_layout.addWidget(status_row)
        main_layout.addWidget(register_row)
        
        return status_container
    
    def _on_theme(self, tokens):
        """Handle theme changes"""
        self._tokens = tokens
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply theme styling"""
        t = self._tokens
        self.camera_label.setStyleSheet(f"""
            QLabel {{
                background: {t['bg.canvas']};
                border: 2px solid {t['border.subtle']};
                border-radius: 8px;
            }}
        """)
        
        status_style = f"color: {t['text.primary']}; background: transparent;"
        self.user_label.setStyleSheet(f"color: {t['accent.primary']}; background: transparent; font-weight: bold;")
        self.emotion_label.setStyleSheet(status_style)
        self.gesture_label.setStyleSheet(status_style)
        self.attention_label.setStyleSheet(status_style)
        
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background: {t['bg.elevated']};
                border: 1px solid {t['border.subtle']};
                border-radius: 6px;
                color: {t['text.primary']};
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {t['accent.primary']};
            }}
        """)
        
        self.register_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['accent.primary']};
                border: none;
                border-radius: 6px;
                color: {t['text.primary']};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {t['accent.hover']};
            }}
            QPushButton:pressed {{
                background: {t['accent.pressed']};
            }}
        """)
    
    def start_camera(self):
        """Start the camera feed"""
        if not self.camera_thread:
            self.camera_thread = CameraThread()
            self.camera_thread.frame_ready.connect(self._on_frame_ready)
            
            # Connect analyzer signals
            self.camera_thread.analyzer.emotion_detected.connect(self._on_emotion)
            self.camera_thread.analyzer.gesture_detected.connect(self._on_gesture)
            self.camera_thread.analyzer.attention_changed.connect(self._on_attention)
            # Don't connect automatic user recognition - only use Face ID dialog
            # self.camera_thread.analyzer.user_recognized.connect(self._on_user_recognized)
            
            self.camera_thread.start()
    
    def stop_camera(self):
        """Stop the camera feed"""
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread.wait()
            self.camera_thread = None
            self.camera_label.clear()
    
    def _on_frame_ready(self, frame, results):
        """Handle new camera frame with analysis results"""
        self.current_frame = frame
        self.current_results = results
        
        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Draw face rectangles
        for (x, y, w, h) in results.get('faces', []):
            color = (0, 255, 0) if results.get('attention') else (255, 165, 0)
            cv2.rectangle(rgb_frame, (x, y), (x+w, y+h), color, 2)
            
            # Draw emotion label
            if results.get('emotion'):
                emotion_text = results['emotion'].capitalize()
                cv2.putText(rgb_frame, emotion_text, (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        # Convert to QImage
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.camera_label.setPixmap(scaled_pixmap)
    
    def _on_emotion(self, emotion, confidence):
        """Handle emotion detection"""
        emotion_emojis = {
            'happy': '😊',
            'neutral': '😐',
            'surprised': '😮',
            'focused': '🤔'
        }
        emoji = emotion_emojis.get(emotion, '😐')
        self.emotion_label.setText(f"{emoji} {emotion.capitalize()}")
        
        # Emit signal for other components
        self.emotion_detected.emit(emotion, confidence)
    
    def _on_gesture(self, gesture):
        """Handle gesture detection"""
        gesture_emojis = {
            'thumbs_up': '👍',
            'palm': '✋',
            'peace': '✌️',
            'point': '☝️',
            'fist': '✊'
        }
        emoji = gesture_emojis.get(gesture, '👋')
        self.gesture_label.setText(f"{emoji} {gesture.replace('_', ' ').title()}")
        
        # Emit signal for other components
        self.gesture_detected.emit(gesture)
    
    def _on_attention(self, is_attentive):
        """Handle attention change"""
        if is_attentive:
            self.attention_label.setText("👀 Attentive")
        else:
            self.attention_label.setText("😴 Distracted")
        
        # Emit signal for other components
        self.attention_changed.emit(is_attentive)
    
    def _on_user_recognized(self, name, confidence):
        """Handle user recognition"""
        if name == "Unknown":
            self.user_label.setText("👤 Guest")
        else:
            self.user_label.setText(f"👤 {name} ({confidence*100:.0f}%)")
        
        # Emit signal for other components (to switch profile)
        self.user_recognized.emit(name, confidence)
    
    def _on_register_user(self):
        """Handle user registration"""
        from PyQt6.QtWidgets import QMessageBox
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter your name")
            return
        
        if not self.camera_thread or not self.current_frame is not None:
            QMessageBox.warning(self, "Error", "Camera not active")
            return
        
        # Register user
        success, message = self.camera_thread.analyzer.register_user(name, self.current_frame)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.name_input.clear()
        else:
            QMessageBox.warning(self, "Error", message)
    
    def showEvent(self, event):
        """Start camera when widget is shown"""
        super().showEvent(event)
        self.start_camera()
    
    def hideEvent(self, event):
        """Stop camera when widget is hidden"""
        super().hideEvent(event)
        self.stop_camera()
    
    def __del__(self):
        try:
            self.stop_camera()
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass
