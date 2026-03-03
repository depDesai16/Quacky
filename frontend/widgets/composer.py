"""
widgets/composer.py — Composer  (stacked pill redesign)

Layout inside pill:
  [ComposerInput — full width, top]
  [MicButton] [ShortcutsButton] [stretch] [SendButton]  ← bottom toolbar row

- Text input sits at the top, full width, no icons crowding it
- Toolbar row sits below with left-aligned action icons + right-aligned send
- Pill border painted via QPainter for crisp 1px HiDPI rendering
- Amber focus ring on the whole pill
- Char counter right-aligned between toolbar and send button
"""

from PyQt6.QtCore    import Qt, pyqtSignal, QEvent, QRectF, QTimer
from PyQt6.QtGui     import (QPainter, QPainterPath, QPen, QColor, QKeyEvent)
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QTextEdit, QSizePolicy, QFrame, QAbstractButton)

from theme import ThemeManager, FONT_STACK



class _ShortcutsButton(QAbstractButton):
    """
    Keyboard icon button — same size as MicButton (32x32).
    No hover background — icon itself highlights to accent colour.
    """
    SIZE = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("Keyboard shortcuts  (Ctrl+/)")
        self._tokens  = ThemeManager.tokens()
        self._hovered = False
        ThemeManager.subscribe(self._on_theme)

    def _on_theme(self, tokens):
        self._tokens = tokens
        self.update()

    def enterEvent(self, e):
        self._hovered = True;  self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    def paintEvent(self, event):
        t  = self._tokens
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.SIZE / 2.0, self.SIZE / 2.0

        icon_color = QColor(t["accent.primary"] if self._hovered else t["text.muted"])
        pen = QPen(icon_color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        kx, ky, kw, kh = cx - 8.0, cy - 5.5, 16.0, 11.0
        kb = QPainterPath()
        kb.addRoundedRect(QRectF(kx, ky, kw, kh), 2.2, 2.2)
        p.drawPath(kb)

        for i in range(3):
            bp = QPainterPath()
            bp.addRoundedRect(QRectF(kx + 2.2 + i * 4.4, ky + 2.2, 3.0, 2.2), 0.5, 0.5)
            p.drawPath(bp)

        sp = QPainterPath()
        sp.addRoundedRect(QRectF(kx + 3.5, ky + kh - 3.5, kw - 7.0, 2.2), 0.5, 0.5)
        p.drawPath(sp)

        p.end()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass



class ComposerInput(QTextEdit):
    send_requested = pyqtSignal()
    MIN_H = 22
    MAX_H = 128

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens = ThemeManager.tokens()
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(self.MIN_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().contentsChanged.connect(self._auto_resize)
        self._apply_style()
        ThemeManager.subscribe(self.apply_theme)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
            return
        super().keyPressEvent(event)

    def _auto_resize(self):
        doc = self.document()
        doc.setTextWidth(self.viewport().width() or 300)
        full_h = int(doc.size().height()) + 8
        h = max(self.MIN_H, min(full_h, self.MAX_H))
        if self.height() != h:
            self.setFixedHeight(h)
        overflow = full_h > self.MAX_H
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
            if overflow else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._auto_resize)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_style()

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(
            "QTextEdit { background: transparent; border: none;"
            " color: " + t["text.primary"] + ";"
            " font-family: " + FONT_STACK + "; font-size: 14px; padding: 0px;"
            " selection-background-color: " + t["selection"] + "; }"
        )
        self.setPlaceholderText("Message Quacky\u2026")

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass



class _ComposerPill(QWidget):
    RADIUS     = 18
    CHAR_LIMIT = 2000
    CHAR_WARN  = 800

    def __init__(self, mic_btn, shortcuts_btn, input_field, send_btn, parent=None):
        super().__init__(parent)
        self._tokens  = ThemeManager.tokens()
        self._focused = False
        self._input   = input_field
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        col = QVBoxLayout(self)
        col.setContentsMargins(14, 12, 12, 10)
        col.setSpacing(8)

        col.addWidget(input_field)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(4)

        toolbar.addWidget(mic_btn,       0, Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(shortcuts_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        toolbar.addStretch(1)

        self._char_label = QLabel("0 / 2000")
        self._char_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(self._char_label, 0, Qt.AlignmentFlag.AlignVCenter)

        toolbar.addSpacing(8)
        toolbar.addWidget(send_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        col.addLayout(toolbar)

        self._update_char_label(0)
        ThemeManager.subscribe(self.apply_theme)
        input_field.installEventFilter(self)
        input_field.document().contentsChanged.connect(self._on_text_changed)

    def eventFilter(self, obj, event):
        if obj is self._input:
            if event.type() == QEvent.Type.FocusIn:
                self._focused = True;  self.update()
            elif event.type() == QEvent.Type.FocusOut:
                self._focused = False; self.update()
        return super().eventFilter(obj, event)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._update_char_label(len(self._input.toPlainText()))
        self.update()

    def _on_text_changed(self):
        self._update_char_label(len(self._input.toPlainText()))

    def _update_char_label(self, n: int):
        t = self._tokens
        remaining = self.CHAR_LIMIT - n
        color = (t["text.secondary"] if n < self.CHAR_WARN
                 else (t["state.warn"] if remaining > 0 else t["state.error"]))
        self._char_label.setStyleSheet(
            "color:" + color + "; font-family:" + FONT_STACK + ";"
            " font-size:11px; background:transparent; border:none;"
        )
        self._char_label.setText(
            str(n) + " / " + str(self.CHAR_LIMIT) if remaining >= 0
            else str(abs(remaining)) + " over limit"
        )

    def paintEvent(self, event):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen_w = 1.0
        inset = pen_w / 2.0
        rect  = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        path  = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)
        p.fillPath(path, QColor(t["bg.elevated"]))
        border_color = QColor(t["accent.primary"] if self._focused else t["border.strong"])
        pen = QPen(border_color, pen_w)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass



class Composer(QWidget):
    """
    Public API:
      input_field     — ComposerInput
      shortcuts_btn   — _ShortcutsButton  (wire .clicked externally)
      set_busy(bool)
      clear()
      text() -> str
    """

    def __init__(self, mic_button, send_button, parent=None):
        super().__init__(parent)
        self._tokens       = ThemeManager.tokens()
        self.input_field   = ComposerInput()
        self.shortcuts_btn = _ShortcutsButton()

        self._pill = _ComposerPill(
            mic_btn       = mic_button,
            shortcuts_btn = self.shortcuts_btn,
            input_field   = self.input_field,
            send_btn      = send_button,
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 16)
        lay.setSpacing(0)
        lay.addWidget(self._pill)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self._pill)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        from PyQt6.QtGui import QColor as _QColor
        shadow.setColor(_QColor(0, 0, 0, 80))
        self._pill.setGraphicsEffect(shadow)

        self._apply_style()
        ThemeManager.subscribe(self.apply_theme)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet("QWidget { background: transparent; border: none; }")

    def set_busy(self, busy: bool):
        self.input_field.setEnabled(not busy)
        self.input_field.setPlaceholderText(
            "Quacky is thinking\u2026" if busy else "Message Quacky\u2026"
        )
        if not busy:
            self.input_field.setFocus()

    def clear(self):
        self.input_field.clear()

    def text(self) -> str:
        return self.input_field.toPlainText()

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
