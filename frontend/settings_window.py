from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen


class ToggleSlider(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked = False, parent = None):
        super().__init__(parent)
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._knob_x = 26.0 if checked else 4.0

        self._anim = QPropertyAnimation(self, b"knob_x", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    # pyqtProperty
    def get_knob_x(self):
        return self._knob_x

    def set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knob_x = pyqtProperty(float, get_knob_x, set_knob_x)

    # State
    def isChecked(self):
        return self._checked

    def setChecked(self, val: bool):
        if val != self._checked:
            self._checked = val
            self._animate_to(26.0 if val else 4.0)

    def _animate_to(self, target: float):
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(target)
        self._anim.start()

    # Interaction
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate_to(26.0 if self._checked else 4.0)
            self.toggled.emit(self._checked)

    # Drawing
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2

        # Track
        if self._checked:
            track_color = QColor("#FFD700")
            track_color.setAlphaF(0.85)
        else:
            track_color = QColor("#2a2a4a")

        pen_width = 1.5
        inset = pen_width / 2
        p.setBrush(QBrush(track_color))
        p.setPen(QPen(QColor("#3a3a6a"), pen_width))
        p.drawRoundedRect(QRectF(inset, inset, w - pen_width, h - pen_width), radius - inset, radius - inset)

        # Knob
        knob_size = h - 6
        p.setBrush(QBrush(QColor("#e8e8e8")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(self._knob_x, 3, knob_size, knob_size))

        p.end()


class SettingsWindow(QWidget):
    model_visibility_changed = pyqtSignal(bool)
    speechtospeech_enabled_changed = pyqtSignal(bool)

    def __init__(self, model_visible: bool, speechtospeech_enabled: bool = False):
        super().__init__()
        self.setWindowTitle("Quacky — Settings")
        self.setFixedSize(260, 120)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)

        with open("css/settings_menu.css", "r") as f:
            self.setStyleSheet(f.read())

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        row = self.build_toggle_row("Model Visibility", model_visible, self.model_visibility_changed)
        root.addLayout(row)
        root.addStretch()

        row = self.build_toggle_row("Speech-to-Speech", speechtospeech_enabled, self.speechtospeech_enabled_changed)
        root.addLayout(row)
        root.addStretch()

    def build_toggle_row(self, label_text: str, initial_state: bool, signal):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        label = QLabel(label_text)
        label.setObjectName("modelSettingLabel")
        row.addWidget(label)
        row.addStretch()
        toggle = ToggleSlider(checked = initial_state)
        toggle.toggled.connect(lambda checked: signal.emit(checked))
        row.addWidget(toggle)
        return row

    def on_toggle(self, checked: bool):
        self.model_visibility_changed.emit(checked)

    def on_speech_toggle(self, checked: bool):
        self.speechtospeech_enabled_changed.emit(checked)