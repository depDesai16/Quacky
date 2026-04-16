from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import (
    QByteArray,
    QBuffer,
    QEventLoop,
    QIODevice,
    QObject,
    QThread,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QImage, QPixmap, QScreen
from PyQt6.QtMultimedia import QMediaCaptureSession, QScreenCapture, QVideoFrame, QVideoSink


@dataclass
class ScreenCaptureResult:
    png_bytes: bytes | None
    method: str
    error: str = ""


def _session_type() -> str:
    return str(os.getenv("XDG_SESSION_TYPE", "")).strip().lower()


def is_wayland_session() -> bool:
    return _session_type() == "wayland"


def _preferred_capture_methods() -> tuple[str, ...]:
    if sys.platform.startswith("win"):
        return ("qt_grab", "powershell")
    if sys.platform.startswith("darwin"):
        return ("qt_grab", "screencapture")
    if _session_type() == "wayland":
        return ("qt_screen_capture", "qt_grab")
    return ("qt_grab", "qt_screen_capture")


def _png_bytes_from_image(image: QImage) -> bytes | None:
    if image.isNull():
        return None
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        return None
    try:
        saved = image.save(buffer, "PNG")
    finally:
        buffer.close()
    if not saved or byte_array.isEmpty():
        return None
    return bytes(byte_array)


def _png_bytes_from_pixmap(pixmap: QPixmap) -> bytes | None:
    if pixmap.isNull():
        return None
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        return None
    try:
        saved = pixmap.save(buffer, "PNG")
    finally:
        buffer.close()
    if not saved or byte_array.isEmpty():
        return None
    return bytes(byte_array)


class _FrameGrabber(QObject):
    def __init__(self, screen: QScreen, timeout_ms: int = 4000, parent=None):
        super().__init__(parent)
        self._screen = screen
        self._timeout_ms = max(500, int(timeout_ms))
        self._image: QImage | None = None
        self._error = ""
        self._loop: QEventLoop | None = None

        self._capture = QScreenCapture(self)
        self._session = QMediaCaptureSession(self)
        self._sink = QVideoSink(self)
        self._session.setScreenCapture(self._capture)
        self._session.setVideoSink(self._sink)
        self._capture.setScreen(self._screen)
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._capture.errorOccurred.connect(self._on_error)

    def _on_frame(self, frame: QVideoFrame):
        if not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        self._image = image
        if self._loop is not None and self._loop.isRunning():
            self._loop.quit()

    def _on_error(self, *_args):
        self._error = self._capture.errorString() or "Qt screen capture failed."
        if self._loop is not None and self._loop.isRunning():
            self._loop.quit()

    def capture_png_bytes(self) -> ScreenCaptureResult:
        self._loop = QEventLoop(self)
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._loop.quit)

        self._capture.start()
        timer.start(self._timeout_ms)
        self._loop.exec()
        self._capture.stop()

        if self._image is None:
            error = self._error or "Timed out waiting for a Wayland screen frame."
            return ScreenCaptureResult(None, "qt_screen_capture", error)

        png_bytes = _png_bytes_from_image(self._image)
        if not png_bytes:
            return ScreenCaptureResult(
                None,
                "qt_screen_capture",
                "Qt screen capture returned an unusable image.",
            )
        return ScreenCaptureResult(png_bytes, "qt_screen_capture")


class _PngEncodeWorker(QObject):
    encoded = pyqtSignal(bytes)
    failed = pyqtSignal(str)

    @pyqtSlot(object)
    def encode(self, image):
        png_bytes = _png_bytes_from_image(image)
        if not png_bytes:
            self.failed.emit("Failed to encode captured frame.")
            return
        self.encoded.emit(png_bytes)


class PersistentScreenCaptureSession(QObject):
    active_changed = pyqtSignal(bool)
    frame_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    encode_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._capture = QScreenCapture(self)
        self._session = QMediaCaptureSession(self)
        self._sink = QVideoSink(self)
        self._session.setScreenCapture(self._capture)
        self._session.setVideoSink(self._sink)
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._capture.errorOccurred.connect(self._on_error)
        self._capture.activeChanged.connect(self._on_active_changed)

        self._latest_png_bytes: bytes | None = None
        self._last_error = ""
        self._frame_counter = 0
        self._encode_in_flight = False
        self._pending_image: QImage | None = None
        self._encoder_thread = QThread(self)
        self._encoder = _PngEncodeWorker()
        self._encoder.moveToThread(self._encoder_thread)
        self.encode_requested.connect(self._encoder.encode)
        self._encoder.encoded.connect(self._on_encoded)
        self._encoder.failed.connect(self._on_encode_failed)
        self._encoder_thread.start()

    def start(self, screen: QScreen | None = None) -> tuple[bool, str]:
        self._last_error = ""
        self._latest_png_bytes = None

        if screen is not None and not is_wayland_session():
            try:
                self._capture.setScreen(screen)
            except Exception:
                pass

        try:
            self._capture.start()
        except Exception as exc:
            self._last_error = str(exc)
            self.error_occurred.emit(self._last_error)
            return False, self._last_error

        if is_wayland_session():
            return True, "Choose a screen or window in the sharing dialog to start screen viewing."
        return True, ""

    def stop(self) -> None:
        try:
            self._capture.stop()
        except Exception:
            pass
        self._latest_png_bytes = None
        self._frame_counter = 0
        self._pending_image = None
        self._encode_in_flight = False
        self.frame_changed.emit(False)

    def is_active(self) -> bool:
        return self._capture.isActive()

    def has_frame(self) -> bool:
        return bool(self._latest_png_bytes)

    def latest_png_bytes(self) -> bytes | None:
        return self._latest_png_bytes

    def latest_frame_id(self) -> int:
        return int(self._frame_counter)

    def last_error(self) -> str:
        return self._last_error

    def wait_for_frame_after(self, last_frame_id: int, timeout_ms: int = 700) -> bool:
        if self._frame_counter > int(last_frame_id):
            return True

        loop = QEventLoop(self)
        timer = QTimer(self)
        timer.setSingleShot(True)

        def _quit_if_newer(_has_frame: bool):
            if self._frame_counter > int(last_frame_id) and loop.isRunning():
                loop.quit()

        self.frame_changed.connect(_quit_if_newer)
        timer.timeout.connect(loop.quit)
        timer.start(max(50, int(timeout_ms)))
        loop.exec()
        try:
            self.frame_changed.disconnect(_quit_if_newer)
        except Exception:
            pass
        return self._frame_counter > int(last_frame_id)

    def _on_frame(self, frame: QVideoFrame):
        if not frame.isValid():
            return
        image = frame.toImage()
        if image.isNull():
            return
        if self._encode_in_flight:
            self._pending_image = image
            return

        self._encode_in_flight = True
        self.encode_requested.emit(image)

    def _on_encoded(self, png_bytes: bytes):
        self._latest_png_bytes = png_bytes
        self._frame_counter += 1
        self._last_error = ""
        self._encode_in_flight = False
        self.frame_changed.emit(True)

        if self._pending_image is not None:
            pending = self._pending_image
            self._pending_image = None
            self._encode_in_flight = True
            self.encode_requested.emit(pending)

    def _on_encode_failed(self, message: str):
        self._last_error = message or "Failed to encode captured frame."
        self._encode_in_flight = False
        self.error_occurred.emit(self._last_error)

        if self._pending_image is not None:
            pending = self._pending_image
            self._pending_image = None
            self._encode_in_flight = True
            self.encode_requested.emit(pending)

    def _on_error(self, *_args):
        self._latest_png_bytes = None
        self._last_error = self._capture.errorString() or "Screen capture failed."
        self.error_occurred.emit(self._last_error)
        self.frame_changed.emit(False)

    def _on_active_changed(self, active: bool):
        if not active:
            self._latest_png_bytes = None
            self._frame_counter = 0
            self._pending_image = None
            self._encode_in_flight = False
            self.frame_changed.emit(False)
        self.active_changed.emit(bool(active))

    def shutdown(self) -> None:
        self.stop()
        self._encoder_thread.quit()
        self._encoder_thread.wait(500)


def _capture_via_qt_grab(screen: QScreen | None) -> ScreenCaptureResult:
    if screen is None:
        return ScreenCaptureResult(None, "qt_grab", "No screen available for Qt grab.")
    pixmap = screen.grabWindow(0)
    png_bytes = _png_bytes_from_pixmap(pixmap)
    if not png_bytes:
        return ScreenCaptureResult(None, "qt_grab", "Qt window grab returned no image.")
    return ScreenCaptureResult(png_bytes, "qt_grab")


def _capture_via_qscreen_capture(screen: QScreen | None) -> ScreenCaptureResult:
    if screen is None:
        return ScreenCaptureResult(None, "qt_screen_capture", "No screen available for screen capture.")
    return _FrameGrabber(screen).capture_png_bytes()


def _capture_via_screencapture() -> ScreenCaptureResult:
    command = shutil.which("screencapture")
    if not command:
        return ScreenCaptureResult(None, "screencapture", "macOS screencapture tool is unavailable.")

    path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = tmp.name
        result = subprocess.run(
            [command, "-x", "-t", "png", path],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip() or "screencapture failed."
            return ScreenCaptureResult(None, "screencapture", stderr)
        data = Path(path).read_bytes()
        if not data:
            return ScreenCaptureResult(None, "screencapture", "screencapture produced an empty file.")
        return ScreenCaptureResult(data, "screencapture")
    except Exception as exc:
        return ScreenCaptureResult(None, "screencapture", str(exc))
    finally:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass


def _capture_via_powershell() -> ScreenCaptureResult:
    command = shutil.which("powershell") or shutil.which("pwsh")
    if not command:
        return ScreenCaptureResult(None, "powershell", "PowerShell is unavailable.")

    script = """
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
$stream = New-Object System.IO.MemoryStream
$bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
[Convert]::ToBase64String($stream.ToArray())
""".strip()

    try:
        result = subprocess.run(
            [command, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip() or "PowerShell capture failed."
            return ScreenCaptureResult(None, "powershell", stderr)
        output = (result.stdout or "").strip()
        if not output:
            return ScreenCaptureResult(None, "powershell", "PowerShell capture returned no data.")
        data = base64.b64decode(output, validate=True)
        if not data:
            return ScreenCaptureResult(None, "powershell", "PowerShell capture returned empty data.")
        return ScreenCaptureResult(data, "powershell")
    except Exception as exc:
        return ScreenCaptureResult(None, "powershell", str(exc))


def capture_screen_png(screen: QScreen | None) -> ScreenCaptureResult:
    errors: list[str] = []
    for method in _preferred_capture_methods():
        if method == "qt_grab":
            result = _capture_via_qt_grab(screen)
        elif method == "qt_screen_capture":
            result = _capture_via_qscreen_capture(screen)
        elif method == "screencapture":
            result = _capture_via_screencapture()
        elif method == "powershell":
            result = _capture_via_powershell()
        else:
            continue

        if result.png_bytes:
            return result
        if result.error:
            errors.append(f"{method}: {result.error}")

    return ScreenCaptureResult(
        None,
        "",
        "; ".join(errors) if errors else "Screen capture failed.",
    )
