"""
widgets/empty_state.py — EmptyState  (duck personality, no chips)

A minimal, character-driven empty state:
  - Large duck avatar (animated gentle pulse)
  - One-liner with Quacky personality
  - Small nudge line — no generic suggestion chips
"""

from PyQt6.QtCore    import (Qt, pyqtSignal, QPropertyAnimation,
                              QEasingCurve, QRectF, pyqtProperty)
from PyQt6.QtGui     import QPainter, QColor, QPainterPath
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSizePolicy,
                              QGraphicsOpacityEffect)

from theme import ThemeManager, FONT_STACK


class _DuckGlow(QWidget):
    """
    Paints a soft amber glow behind the duck emoji label.
    Pulses gently with a QPropertyAnimation on _glow_opacity.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self._glow_opacity = 0.0
        self._tokens = ThemeManager.tokens()

        self._anim = QPropertyAnimation(self, b"glow_opacity", self)
        self._anim.setDuration(2200)
        self._anim.setStartValue(0.08)
        self._anim.setEndValue(0.32)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.start()

        ThemeManager.subscribe(self._on_theme)

    def _on_theme(self, tokens):
        self._tokens = tokens
        self.update()

    @pyqtProperty(float)
    def glow_opacity(self):
        return self._glow_opacity

    @glow_opacity.setter
    def glow_opacity(self, v):
        self._glow_opacity = v
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._tokens["accent.primary"])
        color.setAlphaF(self._glow_opacity)
        cx, cy, r = self.width() / 2, self.height() / 2, 34.0
        path = QPainterPath()
        path.addEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        p.fillPath(path, color)
        p.end()


class EmptyState(QWidget):
    """
    suggestion_clicked signal kept for API compatibility — never emitted.
    """
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, tokens: dict, icon_fn=None, parent=None):
        super().__init__(parent)
        self._tokens  = tokens
        self._icon_fn = icon_fn
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setSpacing(0)
        outer.setContentsMargins(24, 0, 24, 0)

        avatar_container = QWidget()
        avatar_container.setFixedSize(80, 80)
        avatar_container.setStyleSheet("background: transparent; border: none;")

        glow = _DuckGlow(avatar_container)
        glow.move(0, 0)

        duck_lbl = QLabel("🐥", avatar_container)
        duck_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        duck_lbl.setGeometry(0, 0, 80, 80)
        duck_lbl.setStyleSheet(
            "background: transparent; border: none;"
            " font-size: 38px; padding: 0;"
        )

        outer.addWidget(avatar_container, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addSpacing(20)

        self._heading = QLabel("Quack. What\u2019s on your mind?")
        self._heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._heading.setWordWrap(True)
        outer.addWidget(self._heading)
        outer.addSpacing(10)

        self._subtitle = QLabel(
            "Type a message below or press \u00a0Ctrl+/\u00a0 to see what I can do."
        )
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        outer.addWidget(self._subtitle)

        self.apply_theme(tokens)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        t = tokens
        self._heading.setStyleSheet(
            "QLabel { font-family: " + FONT_STACK + "; font-size: 22px;"
            " font-weight: 700; letter-spacing: -0.3px;"
            " color: " + t["text.primary"] + ";"
            " background: transparent; border: none; }"
        )
        self._subtitle.setStyleSheet(
            "QLabel { font-family: " + FONT_STACK + "; font-size: 13px;"
            " font-weight: 400; color: " + t["text.muted"] + ";"
            " background: transparent; border: none; }"
        )