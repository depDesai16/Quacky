from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy

from theme import ThemeManager, FONT_STACK
from widgets.quacky_widget import QuackyBubble


class _Dot(QWidget):
    """A small animated-looking dot for the status hint."""
    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self.setFixedSize(7, 7)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._tokens["accent.primary"])
        c.setAlphaF(0.85)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QRectF(0, 0, 7, 7))
        p.end()


class EmptyState(QWidget):
    suggestion_clicked = pyqtSignal(str)

    def __init__(self, tokens: dict, icon_fn=None, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main wrapper to center everything vertically and horizontally
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setSpacing(0)
        outer.setContentsMargins(20, 12, 20, 12)

        self._content = QWidget(self)
        self._content.setObjectName("emptyStateContent")
        self._content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._content.setMaximumWidth(640)
        self._content.setMinimumWidth(380) # Match bubble width

        content_col = QVBoxLayout(self._content)
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(0)

        # 1. The Animated Quacky Bubble
        self._bubble = QuackyBubble(self._content)
        content_col.addWidget(self._bubble, 0, Qt.AlignmentFlag.AlignHCenter)
        content_col.addSpacing(12) # Tight spacing to connect the graphic to the text

        # 2. Heading
        self._heading = QLabel("How can I help?")
        self._heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._heading.setWordWrap(True)
        content_col.addWidget(self._heading)
        content_col.addSpacing(8)

        # 3. Subtitle
        self._subtitle = QLabel(
            "Ask questions, draft text, or get help with\n"
            "tasks right from your desktop."
        )
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        content_col.addWidget(self._subtitle)
        content_col.addSpacing(24)

        # 4. Status Hints Row
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(0, 0, 0, 0)
        hint_row.setSpacing(8)

        self._dot = _Dot(tokens, self._content)
        hint_row.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)

        self._ready_lbl = QLabel("Ready")
        hint_row.addWidget(self._ready_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._hints_lbl = QLabel("Enter to send   Shift+Enter for newline")
        hint_row.addWidget(self._hints_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        hint_wrap = QWidget(self._content)
        hint_wrap.setLayout(hint_row)
        content_col.addWidget(hint_wrap, 0, Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(self._content, 0, Qt.AlignmentFlag.AlignHCenter)

        # Hook up theming
        ThemeManager.subscribe(self.apply_theme)
        self.apply_theme(tokens)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        t = tokens

        self._content.setStyleSheet("QWidget#emptyStateContent { background: transparent; border: none; }")

        self._heading.setStyleSheet(
            f"QLabel {{"
            f"font-family: {FONT_STACK};"
            f"font-size: 32px;"
            f"font-weight: 700;"
            f"letter-spacing: -0.3px;"
            f"color: {t['text.primary']};"
            f"background: transparent;"
            f"border: none;"
            f"}}"
        )

        self._subtitle.setStyleSheet(
            f"QLabel {{"
            f"font-family: {FONT_STACK};"
            f"font-size: 15px;"
            f"font-weight: 400;"
            f"color: {t['text.secondary']};"
            f"background: transparent;"
            f"border: none;"
            f"}}"
        )

        self._ready_lbl.setStyleSheet(
            f"QLabel {{"
            f"font-family: {FONT_STACK};"
            f"font-size: 12px;"
            f"font-weight: 600;"
            f"color: {t['text.muted']};"
            f"background: transparent;"
            f"border: none;"
            f"}}"
        )

        self._hints_lbl.setStyleSheet(
            f"QLabel {{"
            f"font-family: {FONT_STACK};"
            f"font-size: 12px;"
            f"font-weight: 400;"
            f"color: {t['text.muted']};"
            f"background: transparent;"
            f"border: none;"
            f"}}"
        )

        self._dot.apply_theme(tokens)

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass