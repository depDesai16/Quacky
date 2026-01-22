import sys
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap


class QuackyLogic(QThread):
    update_state_signal = pyqtSignal(str)  # Signal to send data back to UI

    def run(self):
        while True:
            # TODO: Add states
            pass


class QuackyGUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |  # No title bar
            Qt.WindowType.WindowStaysOnTopHint | # Always on top
            Qt.WindowType.Tool                   # Hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Transparent background

        self.setGeometry(1330, 620, 300, 300)
        self.setFixedSize(300, 300)
        self.layout = QVBoxLayout()
        self.label = QLabel(self)
        self.layout.addWidget(self.label)
        pixmap = QPixmap("quackzone1.png")
        scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(scaled_pixmap)
        self.setLayout(self.layout)


if __name__ == "__main__":
    app = QApplication([])
    quacky = QuackyGUI()
    quacky.show()
    sys.exit(app.exec())