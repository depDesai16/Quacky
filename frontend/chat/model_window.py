from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from widgets.card_widget import CardWidget
from .glwidget import GLWidget

class ModelWindow(QWidget):
    def __init__(self):
        """Initialize the instance state."""
        super().__init__()
        self._old_pos = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setWindowTitle("Quacky â€” Model")
        self.setObjectName("quacky-model-window")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 324) 

        self._build_ui()

    def _build_ui(self):
        """Build ui."""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(0)

        self.card = CardWidget()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(28)
        title_bar.setStyleSheet("background: transparent;")
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(10, 0, 6, 0)

        lbl = QLabel("3D Model")
        lbl.setStyleSheet("color: rgba(255,215,0,0.7); font-size: 11px; background: transparent;")
        tb.addWidget(lbl)
        tb.addStretch()

        close_btn = QPushButton("x")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #666688;
                border: none; font-size: 11px;
            }
            QPushButton:hover { color: #ff5555; }
        """)
        close_btn.clicked.connect(self.hide)
        tb.addWidget(close_btn)
        card_layout.addWidget(title_bar)

        import os as _os

        _d = _os.path.dirname(_os.path.abspath(__file__))
        _root = _os.path.dirname(_d)
        self.gl_widget = GLWidget(_os.path.join(_root, "model_3d", "quacky.obj"))
        gl_container = QWidget()
        gl_container.setStyleSheet("background: transparent;")
        gl_layout = QVBoxLayout(gl_container)
        gl_layout.setContentsMargins(6, 0, 6, 6)
        gl_layout.addWidget(self.gl_widget)
        card_layout.addWidget(gl_container)

        root.addWidget(self.card)

    def mousePressEvent(self, event):
        """Handle the mousepress event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Handle the mousemove event."""
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Handle the mouserelease event."""
        self._old_pos = None

