
from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QPainter, QColor, QPainterPath
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QSizePolicy)

from theme import ThemeManager, FONT_STACK

SHORTCUTS = [
    ("General",  [
        ("Ctrl + /",       "Show / hide this panel"),
        ("Ctrl + T",       "Toggle light / dark theme"),
        ("Ctrl + L",       "Focus the message input"),
        ("Escape",         "Clear input or hide window"),
    ]),
    ("Messaging", [
        ("Enter",          "Send message"),
        ("Shift + Enter",  "New line in message"),
    ]),
    ("Window", [
        ("Drag header",    "Move window"),
        ("Drag any edge",  "Resize window"),
    ]),
]


class _KbdChip(QLabel):
    def __init__(self, text: str, tokens: dict, parent=None):
        """Initialize the instance state."""
        super().__init__(text, parent)
        self._tokens = tokens
        self._apply_style()

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self._apply_style()

    def _apply_style(self):
        """Apply style."""
        t = self._tokens
        self.setStyleSheet(f"""
            QLabel {{
                font-family: {FONT_STACK};
                font-size: 11px;
                font-weight: 600;
                color: {t['text.secondary']};
                background: {t['bg.elevated']};
                border: 1px solid {t['border.strong']};
                border-radius: 5px;
                padding: 2px 7px;
            }}
        """)


class ShortcutsPanel(QWidget):
    closed = pyqtSignal()

    RADIUS = 14

    def __init__(self, tokens: dict, parent=None):
        """Initialize the instance state."""
        super().__init__(parent,
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.Tool |
                         Qt.WindowType.WindowStaysOnTopHint)
        self._tokens = tokens
        self.setWindowTitle("Quacky — Shortcuts")
        self.setObjectName("quacky-shortcuts-panel")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(360)

        self._chips  = []
        self._labels = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(0)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 16)
        title = QLabel("Keyboard Shortcuts")
        self._title = title
        title_row.addWidget(title)
        title_row.addStretch()

        hint = QLabel("Esc to close")
        self._hint = hint
        title_row.addWidget(hint)
        outer.addLayout(title_row)

        for section_name, items in SHORTCUTS:
            sec_lbl = QLabel(section_name.upper())
            self._labels.append(("section", sec_lbl))
            outer.addWidget(sec_lbl)
            outer.addSpacing(8)

            for keys, desc in items:
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(8)

                parts = [p.strip() for p in keys.split("+")]
                for i, part in enumerate(parts):
                    chip = _KbdChip(part, tokens)
                    self._chips.append(chip)
                    row.addWidget(chip, 0)
                    if i < len(parts) - 1:
                        plus = QLabel("+")
                        self._labels.append(("plus", plus))
                        row.addWidget(plus, 0)

                row.addSpacing(12)
                desc_lbl = QLabel(desc)
                self._labels.append(("desc", desc_lbl))
                row.addWidget(desc_lbl, 1)
                outer.addLayout(row)
                outer.addSpacing(10)

            outer.addSpacing(10)

        self.apply_theme(tokens)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        for chip in self._chips:
            chip.apply_theme(tokens)
        self._apply_style()

    def _apply_style(self):
        """Apply style."""
        t = self._tokens

        self._title.setStyleSheet(f"""
            QLabel {{
                font-family: {FONT_STACK}; font-size: 15px; font-weight: 700;
                color: {t['text.primary']}; background: transparent; border: none;
            }}
        """)
        self._hint.setStyleSheet(f"""
            QLabel {{
                font-family: {FONT_STACK}; font-size: 11px; font-weight: 400;
                color: {t['text.muted']}; background: transparent; border: none;
            }}
        """)
        for kind, lbl in self._labels:
            if kind == "section":
                lbl.setStyleSheet(f"""
                    QLabel {{
                        font-family: {FONT_STACK}; font-size: 10px; font-weight: 700;
                        letter-spacing: 0.8px; color: {t['text.muted']};
                        background: transparent; border: none; padding-bottom: 0;
                    }}
                """)
            elif kind == "plus":
                lbl.setStyleSheet(f"""
                    QLabel {{
                        font-family: {FONT_STACK}; font-size: 11px;
                        color: {t['text.muted']}; background: transparent; border: none;
                    }}
                """)
            elif kind == "desc":
                lbl.setStyleSheet(f"""
                    QLabel {{
                        font-family: {FONT_STACK}; font-size: 13px;
                        color: {t['text.secondary']}; background: transparent; border: none;
                    }}
                """)
        self.update()

    def paintEvent(self, event):
        """Handle the paint event."""
        t   = self._tokens
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from PyQt6.QtCore import QRectF
        from PyQt6.QtGui import QPen
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)
        p.fillPath(path, QColor(t["bg.elevated"]))
        pen = QPen(QColor(t["border.subtle"]), 1)
        pen.setCosmetic(True)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    def keyPressEvent(self, event):
        """Handle the keypress event."""
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Slash):
            self.close()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle the close event."""
        self.closed.emit()
        super().closeEvent(event)
