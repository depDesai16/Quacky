"""
widgets/empty_state.py - EmptyState

Borderless, theme-aware empty state.
"""

from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFontMetrics
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy

from theme import ThemeManager, FONT_STACK


class _AccentLine(QWidget):
    """Subtle animated-looking accent line without relying on font glyphs."""

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._line_opacity = 0.58
        self.setFixedSize(280, 2)

    def set_opacity(self, value: float):
        self._line_opacity = max(0.0, min(1.0, float(value)))
        self.update()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._tokens["accent.primary"])
        c.setAlphaF(self._line_opacity)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(self.rect()), 1.0, 1.0)
        p.end()


class _Dot(QWidget):
    """Small readiness status dot."""

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
    """
    Borderless empty-state block for the desktop AI assistant.
    `suggestion_clicked` is preserved for API compatibility.
    """

    suggestion_clicked = pyqtSignal(str)

    def __init__(self, tokens: dict, icon_fn=None, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._line_opacity = 0.58
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setSpacing(0)
        outer.setContentsMargins(40, 24, 40, 24)

        self._content = QWidget(self)
        self._content.setObjectName("emptyStateContent")
        self._content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._content.setMaximumWidth(640)
        self._content.setMinimumWidth(300)

        content_col = QVBoxLayout(self._content)
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(0)

        self._accent_top = _AccentLine(tokens, self._content)
        content_col.addWidget(self._accent_top, 0, Qt.AlignmentFlag.AlignHCenter)
        content_col.addSpacing(18)

        self._heading = QLabel("How can I help?")
        self._heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._heading.setWordWrap(True)
        content_col.addWidget(self._heading)
        content_col.addSpacing(8)

        self._subtitle = QLabel(
            "Ask questions, draft text, or get help with\n"
            "tasks right from your desktop."
        )
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setWordWrap(True)
        content_col.addWidget(self._subtitle)
        content_col.addSpacing(16)

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
        content_col.addSpacing(14)

        self._accent_bottom = _AccentLine(tokens, self._content)
        content_col.addWidget(self._accent_bottom, 0, Qt.AlignmentFlag.AlignHCenter)

        outer.addWidget(self._content, 0, Qt.AlignmentFlag.AlignHCenter)

        self._line_blink = QPropertyAnimation(self, b"line_opacity", self)
        self._line_blink.setDuration(1000)
        self._line_blink.setStartValue(0.18)
        self._line_blink.setEndValue(0.92)
        self._line_blink.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._line_blink.setLoopCount(-1)
        self._line_blink.start()

        ThemeManager.subscribe(self.apply_theme)
        self.apply_theme(tokens)
        self._update_accent_width()

    @pyqtProperty(float)
    def line_opacity(self):
        return self._line_opacity

    @line_opacity.setter
    def line_opacity(self, value):
        self._line_opacity = max(0.0, min(1.0, float(value)))
        self._accent_top.set_opacity(self._line_opacity)
        self._accent_bottom.set_opacity(self._line_opacity)

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

        self._accent_top.apply_theme(tokens)
        self._accent_bottom.apply_theme(tokens)
        self._accent_top.set_opacity(self._line_opacity)
        self._accent_bottom.set_opacity(self._line_opacity)
        self._dot.apply_theme(tokens)
        self._update_accent_width()

    def _label_text_width(self, lbl: QLabel) -> int:
        fm = QFontMetrics(lbl.font())
        lines = lbl.text().splitlines() or [lbl.text()]
        return max(fm.horizontalAdvance(line) for line in lines if line) if lines else 0

    def _update_accent_width(self):
        heading_w = self._label_text_width(self._heading)
        subtitle_w = self._label_text_width(self._subtitle)
        target = max(heading_w, subtitle_w)
        target = max(220, target)
        target = min(target, self._content.maximumWidth())
        self._accent_top.setFixedWidth(target)
        self._accent_bottom.setFixedWidth(target)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_accent_width()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
