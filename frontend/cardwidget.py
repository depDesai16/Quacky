from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtWidgets import QWidget

class CardWidget(QWidget):
    RADIUS = 16
    BORDER_COLOR = QColor(255, 215, 0, 190) # rgba(255, 215, 0, 0.75)
    BORDER_WIDTH = 2
    BG_COLOR = QColor(10, 10, 22, 230)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        hw = self.BORDER_WIDTH // 2
        rect = self.rect().adjusted(hw, hw, -hw, -hw)

        from PyQt6.QtCore import QRectF
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.RADIUS, self.RADIUS)

        # Fill
        p.fillPath(path, self.BG_COLOR)

        # Border
        pen = QPen(self.BORDER_COLOR, self.BORDER_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)

        p.end()