"""
Camera module for face recognition and analysis
"""
from .camera_view import CameraView
from .camera_analyzer import CameraAnalyzer
from .face_recognition import FaceRecognitionManager
from .face_id_dialog import FaceIDDialog

__all__ = [
    'CameraView',
    'CameraAnalyzer',
    'FaceRecognitionManager',
    'FaceIDDialog',
]
