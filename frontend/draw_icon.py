from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath, QBrush, QPen

def draw_icon():
    size = 60
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)

    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Head (round, front-facing)
    p.setBrush(QBrush(QColor("#FFD700")))
    p.setPen(QPen(QColor("#CC9900"), 1.5))
    p.drawEllipse(6, 4, 52, 52)

    # Fluffy cheeks
    p.setBrush(QBrush(QColor("#FFBE00")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 30, 16, 12)   # left cheek
    p.drawEllipse(44, 30, 16, 12)  # right cheek

    # Eyes: whites
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.setPen(QPen(QColor("#CCAA00"), 1))
    p.drawEllipse(13, 16, 16, 18)  # left eye
    p.drawEllipse(35, 16, 16, 18)  # right eye

    # Eyes: pupils
    p.setBrush(QBrush(QColor("#1a1a2e")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(18, 21, 8, 9)    # left pupil
    p.drawEllipse(40, 21, 8, 9)    # right pupil

    # Eyes: shine
    p.setBrush(QBrush(QColor("#FFFFFF")))
    p.drawEllipse(20, 22, 3, 3)    # left shine
    p.drawEllipse(42, 22, 3, 3)    # right shine

    # Bill (flat oval, centered)
    p.setBrush(QBrush(QColor("#FF8C00")))
    p.setPen(QPen(QColor("#CC6000"), 1.5))
    bill = QPainterPath()
    bill.moveTo(32, 36)
    bill.cubicTo(20, 34, 18, 44, 32, 45)
    bill.cubicTo(46, 44, 44, 34, 32, 36)
    p.drawPath(bill)

    # Smile line
    p.setPen(QPen(QColor("#CC6000"), 1.2))
    p.drawLine(22, 40, 42, 40)

    # Tuft on top
    p.setBrush(QBrush(QColor("#FFD700")))
    p.setPen(QPen(QColor("#CC9900"), 1))
    tuft = QPainterPath()
    tuft.moveTo(28, 6)
    tuft.cubicTo(26, -2, 32, -4, 32, 3)
    tuft.cubicTo(32, -4, 38, -2, 36, 6)
    p.drawPath(tuft)

    p.end()
    return QIcon(px)