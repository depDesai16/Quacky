"""Camera module exports with lazy loading."""

__all__ = [
    "CameraView",
    "CameraAnalyzer",
    "FaceRecognitionManager",
    "FaceIDDialog",
]


def __getattr__(name: str):
    if name == "CameraView":
        from .camera_view import CameraView

        return CameraView
    if name == "CameraAnalyzer":
        from .camera_analyzer import CameraAnalyzer

        return CameraAnalyzer
    if name == "FaceRecognitionManager":
        from .face_recognition import FaceRecognitionManager

        return FaceRecognitionManager
    if name == "FaceIDDialog":
        from .face_id_dialog import FaceIDDialog

        return FaceIDDialog
    raise AttributeError(name)
