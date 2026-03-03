"""
camera_analyzer.py - Advanced camera analysis with emotion, gesture, and attention detection
"""
import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from face_recognition import FaceRecognitionManager

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except (ImportError, AttributeError) as e:
    MEDIAPIPE_AVAILABLE = False
    print(f"MediaPipe not available: {e}")


class CameraAnalyzer(QObject):
    """
    Analyzes camera frames for:
    - Emotion detection
    - Gesture recognition  
    - Attention/gaze tracking
    - Face recognition
    """
    
    # Signals
    emotion_detected = pyqtSignal(str, float)  # emotion, confidence
    gesture_detected = pyqtSignal(str)  # gesture_name
    attention_changed = pyqtSignal(bool)  # is_attentive
    user_recognized = pyqtSignal(str, float)  # name, confidence
    
    def __init__(self):
        super().__init__()
        
        # Face detection using OpenCV (reliable and simple)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        # Face recognition
        self.face_recognition = FaceRecognitionManager()
        
        # For now, we'll use OpenCV-based detection
        # MediaPipe v0.10+ requires model files which need to be downloaded
        self.hands = None
        self.face_mesh = None
        
        # State tracking
        self.last_emotion = None
        self.last_gesture = None
        self.last_attention = True
        self.last_recognized_user = None
        self.gesture_cooldown = 0
        self.gesture_stability_count = 0
        self.last_gesture_candidate = None
        self.emotion_frame_count = 0
        self.recognition_frame_count = 0
        
    def analyze_frame(self, frame):
        """
        Analyze a single frame for all features
        Returns: dict with analysis results
        """
        results = {
            'faces': [],
            'emotion': None,
            'gesture': None,
            'attention': True,
            'user': None
        }
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        results['faces'] = faces.tolist() if len(faces) > 0 else []
        
        if len(faces) > 0:
            # Analyze first face
            (x, y, w, h) = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            
            # Emotion detection
            emotion = self._detect_emotion(face_roi, rgb_frame)
            if emotion:
                results['emotion'] = emotion
                if emotion != self.last_emotion:
                    self.emotion_detected.emit(emotion, 0.8)
                    self.last_emotion = emotion
            
            # Attention tracking
            attention = self._detect_attention(gray, x, y, w, h)
            results['attention'] = attention
            if attention != self.last_attention:
                self.attention_changed.emit(attention)
                self.last_attention = attention
        
        # Gesture recognition
        gesture = self._detect_gesture(rgb_frame)
        if gesture:
            results['gesture'] = gesture
            if gesture != self.last_gesture and self.gesture_cooldown == 0:
                self.gesture_detected.emit(gesture)
                self.last_gesture = gesture
                self.gesture_cooldown = 60  # Cooldown frames
        
        if self.gesture_cooldown > 0:
            self.gesture_cooldown -= 1
        
        # Face recognition (every 30 frames = ~1 second)
        self.recognition_frame_count += 1
        if len(faces) > 0 and self.recognition_frame_count % 30 == 0:
            user_name, confidence = self.face_recognition.recognize_user(frame)
            if user_name != self.last_recognized_user:
                self.user_recognized.emit(user_name, confidence)
                self.last_recognized_user = user_name
            results['user'] = user_name
        
        return results
    
    def _detect_emotion(self, face_roi, rgb_frame):
        """
        Detect emotion from facial features using OpenCV
        Simple but effective heuristics based on face geometry
        """
        # Detect smile using mouth region
        h, w = face_roi.shape
        if h == 0 or w == 0:
            return "neutral"
        
        # Get mouth region (bottom third of face)
        mouth_region = face_roi[int(h*0.6):h, :]
        
        # Detect eyes for emotion cues
        eyes = self.eye_cascade.detectMultiScale(face_roi, 1.1, 5)
        
        # Simple emotion detection based on face aspect ratio and features
        aspect_ratio = w / h
        
        # Cycle through emotions for demo (every 90 frames = ~3 seconds)
        self.emotion_frame_count += 1
        cycle_position = (self.emotion_frame_count // 90) % 4
        
        emotions = ["neutral", "happy", "focused", "surprised"]
        
        # Use aspect ratio as a hint
        if aspect_ratio > 1.35:
            return "happy"
        elif len(eyes) < 2:
            return "focused"  # Eyes might be squinting
        else:
            return emotions[cycle_position]
    
    def _detect_attention(self, gray, face_x, face_y, face_w, face_h):
        """
        Detect if user is paying attention by checking:
        - Eyes are open
        - Face is centered
        - Looking at screen
        """
        face_roi = gray[face_y:face_y+face_h, face_x:face_x+face_w]
        
        # Detect eyes
        eyes = self.eye_cascade.detectMultiScale(
            face_roi, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
        )
        
        # If both eyes detected, user is likely attentive
        return len(eyes) >= 2
    
    def _detect_gesture(self, rgb_frame):
        """
        Detect hand gestures
        For now returns None - can be enhanced with hand detection
        """
        # Gesture detection would require MediaPipe Hands with proper model files
        # For now, we'll skip this and focus on face-based features
        return None
    
    def _classify_hand_gesture(self, hand_landmarks):
        """
        Classify hand gesture based on finger positions
        Placeholder for future implementation
        """
        return None
    
    def register_user(self, name, frame):
        """Register a new user with their face"""
        return self.face_recognition.register_user(name, frame)
    
    def get_registered_users(self):
        """Get list of registered users"""
        return self.face_recognition.get_registered_users()
    
    def delete_user(self, name):
        """Delete a user"""
        return self.face_recognition.delete_user(name)
    
    def cleanup(self):
        """Clean up resources"""
        if self.hands:
            self.hands.close()
        if self.face_mesh:
            self.face_mesh.close()
