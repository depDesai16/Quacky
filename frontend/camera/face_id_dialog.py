"""
face_id_dialog.py - Face ID authentication dialog (Apple-style)
"""
import os
import sys

import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout
from theme import FONT_FAMILY_UI, ThemeManager


class FaceIDDialog(QDialog):
    """
    Apple-style Face ID authentication dialog
    Shows camera feed and automatically recognizes user
    """
    
    user_authenticated = pyqtSignal(str, float)  # name, confidence
    
    def __init__(self, face_recognition_manager, parent=None):
        super().__init__(parent)
        self.face_recognition = face_recognition_manager
        self._tokens = ThemeManager.tokens()
        
        self.cap = None
        self.timer = None
        self.attempts = 0
        self.max_attempts = 10  # Try for ~3 seconds
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self._face_cascade.empty():
            self._face_cascade = None
        
        self.setWindowTitle("Face ID Authentication")
        self.setModal(True)
        self.setMinimumSize(400, 500)
        self.resize(400, 500)
        
        # Frameless with rounded corners
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._build_ui()
        self._apply_theme()
        ThemeManager.subscribe(self._on_theme)
    
    def _build_ui(self):
        """Build the Face ID UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        self.title_label = QLabel("Face ID")
        title_font = QFont(FONT_FAMILY_UI)
        title_font.setPointSizeF(20)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status message
        self.status_label = QLabel("Position your face in the frame")
        status_font = QFont(FONT_FAMILY_UI)
        status_font.setPointSizeF(13)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        
        # Camera preview
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(300, 300)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setScaledContents(False)
        
        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.cancel_btn)
    
    def _on_theme(self, tokens):
        """Handle theme changes"""
        self._tokens = tokens
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply theme styling"""
        t = self._tokens
        
        self.setStyleSheet(f"""
            QDialog {{
                background: {t['bg.surface']};
                border: 2px solid {t['border.strong']};
                border-radius: 16px;
            }}
        """)
        
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {t['text.primary']};
                background: transparent;
            }}
        """)
        
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {t['text.secondary']};
                background: transparent;
            }}
        """)
        
        self.camera_label.setStyleSheet(f"""
            QLabel {{
                background: {t['bg.canvas']};
                border: 2px solid {t['border.subtle']};
                border-radius: 12px;
            }}
        """)
        
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['bg.elevated']};
                border: 1px solid {t['border.subtle']};
                border-radius: 8px;
                color: {t['text.primary']};
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {t['bg.surface']};
                border-color: {t['border.strong']};
            }}
        """)
    
    def showEvent(self, event):
        """Start camera when dialog is shown"""
        super().showEvent(event)
        self.start_authentication()
    
    def hideEvent(self, event):
        """Stop camera when dialog is hidden"""
        super().hideEvent(event)
        self.stop_authentication()
    
    def start_authentication(self):
        """Start Face ID authentication"""
        self.attempts = 0
        self.status_label.setText("Looking for your face...")
        
        # Open camera with optimized settings
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_label.setText("❌ Camera not available")
            return
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Lower resolution for speed
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer lag
        
        # Start timer to check for face
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_face)
        self.timer.start(100)  # Check every 100ms for smooth video
    
    def stop_authentication(self):
        """Stop authentication"""
        if self.timer:
            self.timer.stop()
            self.timer = None
        
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def _check_face(self):
        """Check for face and try to recognize"""
        if not self.cap or not self.cap.isOpened():
            self.status_label.setText("❌ Camera not available")
            self.stop_authentication()
            return
        
        ret, frame = self.cap.read()
        if not ret:
            return
        
        # Display frame with face detection box
        self._display_frame(frame)
        
        # Only try recognition every 5 frames to reduce lag
        if self.attempts % 5 == 0:
            # Try to recognize user
            name, confidence = self.face_recognition.recognize_user(frame)
            
            # Show debug info
            if name == "Unknown":
                self.status_label.setText("Looking for your face...")
            else:
                self.status_label.setText(f"Found: {name} ({confidence*100:.0f}% match)")
            
            # Lower threshold for better recognition
            if name != "Unknown" and confidence > 0.4:  # Even lower threshold
                # Success!
                self.status_label.setText(f"✓ Authenticated as {name}")
                self.stop_authentication()
                
                # Emit signal and close
                QTimer.singleShot(500, lambda: self._complete_auth(name, confidence))
                return
        
        self.attempts += 1
        if self.attempts >= 150:  # 15 seconds at 100ms intervals
            registered_users = self.face_recognition.get_registered_users()
            if registered_users:
                self.status_label.setText(
                    f"❌ Face not recognized\n"
                    f"Registered users: {', '.join(registered_users)}\n"
                    f"Try registering again in better lighting"
                )
            else:
                self.status_label.setText("❌ No registered users\nPlease register your face first")
            self.stop_authentication()
    
    def _complete_auth(self, name, confidence):
        """Complete authentication"""
        self.user_authenticated.emit(name, confidence)
        self.accept()
    
    def _display_frame(self, frame):
        """Display camera frame with face detection box"""
        # Detect faces to show visual feedback
        faces = []
        if self._face_cascade is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(50, 50),
            )
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Draw face rectangles for visual feedback
        for (x, y, w, h) in faces:
            cv2.rectangle(rgb_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(rgb_frame, "Face Detected", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Convert to QImage
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation  # Faster scaling
        )
        
        self.camera_label.setPixmap(scaled_pixmap)
    
    def __del__(self):
        try:
            self.stop_authentication()
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass
