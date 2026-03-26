"""
Camera module for face recognition and analysis
"""
from .camera_analyzer import CameraAnalyzer
from .camera_view import CameraView
from .face_id_dialog import FaceIDDialog
from .face_recognition import FaceRecognitionManager

__all__ = [
    'CameraView',
    'CameraAnalyzer',
    'FaceRecognitionManager',
    'FaceIDDialog',
]
