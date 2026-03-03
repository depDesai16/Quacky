"""
widgets/thinking_bubble.py — ThinkingBubble  (wave edition)

Three dots animate in a smooth rolling wave — each dot moves up then back
down with a 160 ms stagger between them. Much more polished than the old
opacity-only pulse.

  • Dot size: 7 px  — slightly smaller for a refined look
  • Wave height: 6 px vertical travel
  • Duration: 560 ms per cycle, looping
  • Stagger: 160 ms between dots
  • Easing: InOutSine — smooth and natural
"""

from PyQt6.QtCore    import (Qt, QPropertyAnimation, QEasingCurve,
                              pyqtProperty, QRectF, QTimer)
from PyQt6.QtGui     import QPainter, QColor, QBrush
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QFrame, QSizePolicy)

from theme import ThemeManager

DOT_SIZE    = 7
DOT_SPACING = 7
DOT_COUNT   = 3
WAVE_H      = 6                             
DURATION_MS = 560
STAGGER_MS  = 160


class _WaveDot(QWidget):
    """
    A dot that animates its _offset_y (0 → -WAVE_H → 0).
    Drawn with QPainter so it can go outside its natural bounds.
    """

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color    = color
        self._offset_y = 0.0
        self.setFixedSize(DOT_SIZE, DOT_SIZE + WAVE_H)

    def set_color(self, color: QColor):
        self._color = color
        self.update()

    def _get_offset_y(self) -> float:
        return self._offset_y

    def _set_offset_y(self, v: float):
        self._offset_y = v
        self.update()

    offset_y = pyqtProperty(float, _get_offset_y, _set_offset_y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        p.setBrush(QBrush(c))
        p.setPen(Qt.PenStyle.NoPen)
        y = WAVE_H + self._offset_y                                          
        p.drawEllipse(QRectF(0, y, DOT_SIZE, DOT_SIZE))
        p.end()


class ThinkingBubble(QFrame):
    """
    Bubble-shaped container with three wave-animated dots.
    Matches AssistantBubble visual style (asst.bg / asst.border).
    """

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens    = tokens
        self._dot_color = QColor(tokens["accent.primary"])
        self._dot_color.setAlphaF(0.75)
        self._apply_style()
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(DOT_SPACING)

        self._dots  = []
        self._anims = []

        for i in range(DOT_COUNT):
            dot = _WaveDot(QColor(self._dot_color), self)
            layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignBottom)
            self._dots.append(dot)

        self._start_animations()

    def _start_animations(self):
        for i, dot in enumerate(self._dots):
            anim = QPropertyAnimation(dot, b"offset_y", self)
            anim.setDuration(DURATION_MS)
            anim.setStartValue(0.0)
            anim.setKeyValueAt(0.25, -float(WAVE_H))            
            anim.setKeyValueAt(0.55,  0.0)                                
            anim.setKeyValueAt(1.0,   0.0)                            
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            anim.setLoopCount(-1)
            self._anims.append(anim)
            QTimer.singleShot(i * STAGGER_MS, anim.start)

    def stop_animations(self):
        for a in self._anims:
            a.stop()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        c = QColor(tokens["accent.primary"])
        c.setAlphaF(0.75)
        self._dot_color = c
        self._apply_style()
        for dot in self._dots:
            dot.set_color(QColor(c))

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QFrame {{
                background: {t['asst.bg']};
                border: 1px solid {t['asst.border']};
                border-top-left-radius: 4px;
                border-top-right-radius: 14px;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }}
        """)