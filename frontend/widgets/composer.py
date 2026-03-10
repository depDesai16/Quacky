from PyQt6.QtCore    import Qt, pyqtSignal, QEvent, QRectF, QTimer, QPoint, QPointF
from PyQt6.QtGui     import (QPainter, QPainterPath, QPen, QColor, QKeyEvent)
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QTextEdit, QSizePolicy, QFrame, QAbstractButton,
                              QMenu, QStackedWidget, QApplication)

from theme import ThemeManager, FONT_STACK, FONT_FAMILY_UI


class _MenuIcon(QWidget):
    """Small fixed-size widget that paints a vector icon for menu rows."""
    SIZE = 18

    def __init__(self, kind: str, tokens: dict, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._kind    = kind
        self._tokens  = tokens
        self._hovered = False
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_hovered(self, hovered: bool):
        """Set hovered state and repaint."""
        self._hovered = hovered
        self.update()

    def paintEvent(self, _event):
        """Handle the paint event."""
        t  = self._tokens
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s  = float(self.SIZE)
        cx = s / 2.0

        color = QColor(t["accent.primary"] if self._hovered else t["text.secondary"])
        pen = QPen(color, 1.25)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._kind in ("camera", "camera_close"):
            body = QPainterPath()
            body.addRoundedRect(QRectF(2.0, 5.5, 13.0, 9.0), 1.8, 1.8)
            p.drawPath(body)
            p.drawEllipse(QRectF(5.5, 7.5, 6.0, 5.0))
            bump = QPainterPath()
            bump.addRoundedRect(QRectF(5.5, 3.0, 4.5, 3.0), 1.0, 1.0)
            p.drawPath(bump)
            if self._kind == "camera_close":
                pen2 = QPen(color, 1.4, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen2)
                arm = 2.2
                p.drawLine(QPointF(cx - arm, cx - arm), QPointF(cx + arm, cx + arm))
                p.drawLine(QPointF(cx - arm, cx + arm), QPointF(cx + arm, cx - arm))

        elif self._kind == "shortcuts":
            kb = QPainterPath()
            kb.addRoundedRect(QRectF(1.5, 5.0, 15.0, 9.5), 1.8, 1.8)
            p.drawPath(kb)
            for i in range(3):
                kr = QPainterPath()
                kr.addRoundedRect(QRectF(3.0 + i * 4.3, 6.8, 3.0, 2.2), 0.5, 0.5)
                p.drawPath(kr)
            sp = QPainterPath()
            sp.addRoundedRect(QRectF(4.5, 10.5, 9.0, 2.2), 0.5, 0.5)
            p.drawPath(sp)

        p.end()


class _PlusMenuButton(QAbstractButton):
    """A + button that opens a dropdown menu for Camera and Shortcuts."""

    camera_clicked    = pyqtSignal()
    shortcuts_clicked = pyqtSignal()

    SIZE = 32

    def __init__(self, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("More options")
        self._tokens         = ThemeManager.tokens()
        self._hovered        = False
        self._camera_active  = False
        ThemeManager.subscribe(self._on_theme)

    def set_camera_active(self, active: bool):
        """Mark whether the camera panel is currently shown."""
        self._camera_active = active
        self.update()

    def _on_theme(self, tokens):
        """Handle theme callbacks."""
        self._tokens = tokens
        self.update()

    def enterEvent(self, e):
        """Handle the enter event."""
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        """Handle the leave event."""
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        """Handle the paint event."""
        t  = self._tokens
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.SIZE / 2.0, self.SIZE / 2.0
        arm = 6.0

        active = self._hovered or self._camera_active
        icon_color = QColor(t["accent.primary"] if active else t["text.secondary"])

        pen = QPen(icon_color, 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Subtle circular background on hover
        if self._hovered:
            bg = QColor(t["accent.primary"])
            bg.setAlphaF(0.10)
            p.setBrush(bg)
            p.setPen(Qt.PenStyle.NoPen)
            r = self.SIZE / 2.0 - 1.5
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)

        # Always draw +
        p.drawLine(QPointF(cx - arm, cy),      QPointF(cx + arm, cy))
        p.drawLine(QPointF(cx,       cy - arm), QPointF(cx,       cy + arm))

        p.end()

    def mousePressEvent(self, event):
        """Handle the mousepress event."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_menu()
        super().mousePressEvent(event)


    def _make_menu_row(self, kind: str, label: str, subtitle: str, tokens: dict) -> "QWidget":
        """Build a polished full-width menu row with icon, label, subtitle and hover accent bar."""
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout
        t = tokens

        row = QWidget()
        row.setObjectName("menuRow")
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        row.setMinimumWidth(190)

        outer = QHBoxLayout(row)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left accent bar (painted via a tiny widget)
        accent_bar = QWidget()
        accent_bar.setObjectName("accentBar")
        accent_bar.setFixedWidth(3)
        outer.addWidget(accent_bar)

        # Inner content
        inner = QWidget()
        inner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        inner_lay = QHBoxLayout(inner)
        inner_lay.setContentsMargins(12, 10, 18, 10)
        inner_lay.setSpacing(12)
        outer.addWidget(inner, 1)

        # Icon
        icon_widget = _MenuIcon(kind=kind, tokens=t)
        icon_widget.setObjectName("rowIcon")
        inner_lay.addWidget(icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        # Text column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(1)

        lbl = QLabel(label)
        lbl.setObjectName("rowLabel")
        lbl.setStyleSheet(
            f"color: {t['text.primary']}; background: transparent; border: none;"
            f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
            f" font-size: 13px; font-weight: 500;"
        )
        text_col.addWidget(lbl)

        sub = QLabel(subtitle)
        sub.setObjectName("rowSub")
        sub.setStyleSheet(
            f"color: {t['text.muted']}; background: transparent; border: none;"
            f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
            f" font-size: 11px; font-weight: 400;"
        )
        text_col.addWidget(sub)
        inner_lay.addLayout(text_col, 1)

        # Hover state: paint background + accent bar + recolor text
        row._hovered    = False
        row._accent_bar = accent_bar
        row._lbl        = lbl
        row._sub        = sub
        row._icon_w     = icon_widget
        row._t          = t
        row._kind       = kind

        def _enter(ev):
            row._hovered = True
            accent_bar.setStyleSheet(
                f"QWidget#accentBar {{ background: {t['accent.primary']};"
                f" border-top-left-radius: 3px; border-bottom-left-radius: 3px; }}"
            )
            inner.setStyleSheet(
                f"QWidget {{ background: {t['accent.subtleBg']}; border-radius: 0px; }}"
            )
            lbl.setStyleSheet(
                f"color: {t['accent.primary']}; background: transparent; border: none;"
                f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
                f" font-size: 13px; font-weight: 600;"
            )
            sub.setStyleSheet(
                f"color: {t['accent.primary']}; background: transparent; border: none;"
                f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
                f" font-size: 11px; font-weight: 400; opacity: 0.7;"
            )
            icon_widget.set_hovered(True)

        def _leave(ev):
            row._hovered = False
            accent_bar.setStyleSheet(
                "QWidget#accentBar { background: transparent; }"
            )
            inner.setStyleSheet("QWidget { background: transparent; }")
            lbl.setStyleSheet(
                f"color: {t['text.primary']}; background: transparent; border: none;"
                f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
                f" font-size: 13px; font-weight: 500;"
            )
            sub.setStyleSheet(
                f"color: {t['text.muted']}; background: transparent; border: none;"
                f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
                f" font-size: 11px;"
            )
            icon_widget.set_hovered(False)

        # Init resting state
        accent_bar.setStyleSheet("QWidget#accentBar { background: transparent; }")
        inner.setStyleSheet("QWidget { background: transparent; }")

        row.enterEvent = _enter
        row.leaveEvent = _leave
        return row

    def _show_menu(self):
        """Build and display the dropdown menu."""
        from PyQt6.QtWidgets import QWidgetAction, QVBoxLayout
        t = self._tokens

        menu = QMenu(self)
        menu.setContentsMargins(0, 0, 0, 0)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setWindowFlags(
            menu.windowFlags()
            | Qt.WindowType.FramelessWindowHint
        )

        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t['bg.elevated']};
                border: 1px solid {t['border.strong']};
                border-radius: 12px;
                padding: 0px;
            }}
            QMenu::separator {{
                height: 1px;
                background: {t['border.subtle']};
                margin: 0px 0px;
            }}
        """)

        # Header label
        header_widget = QWidget()
        header_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        hl = QHBoxLayout(header_widget)
        hl.setContentsMargins(15, 9, 15, 6)
        header_lbl = QLabel("Quick Access")
        header_lbl.setStyleSheet(
            f"color: {t['text.muted']}; background: transparent; border: none;"
            f" font-family: '{FONT_FAMILY_UI}', sans-serif;"
            f" font-size: 10px; font-weight: 700; letter-spacing: 0.8px;"
        )
        hl.addWidget(header_lbl)
        header_action = QWidgetAction(menu)
        header_action.setDefaultWidget(header_widget)
        header_action.setEnabled(False)
        menu.addAction(header_action)

        menu.addSeparator()

        # Camera action
        cam_kind     = "camera_close" if self._camera_active else "camera"
        cam_label    = "Close Camera"  if self._camera_active else "Camera"
        cam_subtitle = "Hide camera view" if self._camera_active else "Open camera view"
        cam_row      = self._make_menu_row(cam_kind, cam_label, cam_subtitle, t)
        cam_action   = QWidgetAction(menu)
        cam_action.setDefaultWidget(cam_row)
        menu.addAction(cam_action)

        menu.addSeparator()

        # Shortcuts action
        sc_row    = self._make_menu_row("shortcuts", "Shortcuts", "Ctrl+/  to open anytime", t)
        sc_action = QWidgetAction(menu)
        sc_action.setDefaultWidget(sc_row)
        menu.addAction(sc_action)

        # Bottom padding spacer
        spacer_w = QWidget()
        spacer_w.setFixedHeight(4)
        spacer_w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        spacer_a = QWidgetAction(menu)
        spacer_a.setDefaultWidget(spacer_w)
        spacer_a.setEnabled(False)
        menu.addAction(spacer_a)

        # Row click handlers
        def _row_click(action, signal):
            def _handler(ev):
                menu.close()
                signal.emit()
            return _handler

        cam_row.mousePressEvent = _row_click(cam_action, self.camera_clicked)
        sc_row.mousePressEvent  = _row_click(sc_action,  self.shortcuts_clicked)

        # Pop up directly above the button, left-aligned
        global_pos = self.mapToGlobal(QPoint(0, 0))
        hint = menu.sizeHint()
        x = global_pos.x()
        y = global_pos.y() - hint.height() - 6
        screen = QApplication.screenAt(global_pos) or QApplication.primaryScreen()
        if screen is not None:
            sg = screen.availableGeometry()
            x = max(sg.left(), min(x, sg.right() - hint.width() + 1))
            if y < sg.top():
                y = global_pos.y() + self.height() + 6
            y = max(sg.top(), min(y, sg.bottom() - hint.height() + 1))
        menu.exec(QPoint(x, y))

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass



class ComposerInput(QTextEdit):
    send_requested = pyqtSignal()
    MIN_H = 22
    MAX_H = 128

    def __init__(self, parent=None):
        """Initialize the instance state."""
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
        """Handle the keypress event."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
            return
        super().keyPressEvent(event)

    def _auto_resize(self):
        """Handle auto resize."""
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
        """Handle the resize event."""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._auto_resize)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self._apply_style()

    def _apply_style(self):
        """Apply style."""
        t = self._tokens
        self.setStyleSheet(
            "QTextEdit { background: transparent; border: none;"
            " color: " + t["text.primary"] + ";"
            " font-family: " + FONT_STACK + "; font-size: 14px; padding: 0px;"
            " selection-background-color: " + t["selection"] + "; }"
        )
        self.setPlaceholderText("Message Quacky\u2026")

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass



class _ComposerPill(QWidget):
    RADIUS     = 18
    CHAR_LIMIT = 2000
    CHAR_WARN  = 800

    def __init__(self, mic_btn, plus_btn, input_field, send_btn, sts_btn, parent=None):
        """Initialize the instance state."""
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

        toolbar.addWidget(mic_btn,  0, Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(plus_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        toolbar.addStretch(1)

        self._char_label = QLabel("0 / 2000")
        self._char_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(self._char_label, 0, Qt.AlignmentFlag.AlignVCenter)

        toolbar.addSpacing(8)

        # Stacked button: index 0 = sts, index 1 = send — use fixed SIZE from the button class
        self._btn_stack = QStackedWidget()
        self._btn_stack.setFixedSize(32, 32)
        self._btn_stack.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_stack.addWidget(sts_btn)   # index 0
        self._btn_stack.addWidget(send_btn)  # index 1
        self._btn_stack.setCurrentIndex(0)
        toolbar.addWidget(self._btn_stack, 0, Qt.AlignmentFlag.AlignVCenter)
        col.addLayout(toolbar)

        self._update_char_label(0)
        ThemeManager.subscribe(self.apply_theme)
        input_field.installEventFilter(self)
        input_field.document().contentsChanged.connect(self._on_text_changed)

    def set_has_text(self, has_text: bool):
        """Switch between sts (0) and send (1) button."""
        self._btn_stack.setCurrentIndex(1 if has_text else 0)

    def eventFilter(self, obj, event):
        """Handle eventfilter."""
        if obj is self._input:
            if event.type() == QEvent.Type.FocusIn:
                self._focused = True;  self.update()
            elif event.type() == QEvent.Type.FocusOut:
                self._focused = False; self.update()
        return super().eventFilter(obj, event)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        self._update_char_label(len(self._input.toPlainText()))
        self.update()

    def _on_text_changed(self):
        """Handle text changed callbacks."""
        self._update_char_label(len(self._input.toPlainText()))

    def _update_char_label(self, n: int):
        """Update char label."""
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
        """Handle the paint event."""
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
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass



class Composer(QWidget):

    def __init__(self, mic_button, send_button, sts_button, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._tokens       = ThemeManager.tokens()
        self.input_field   = ComposerInput()
        self.plus_btn      = _PlusMenuButton()

        self._pill = _ComposerPill(
            mic_btn    = mic_button,
            plus_btn   = self.plus_btn,
            input_field= self.input_field,
            send_btn   = send_button,
            sts_btn    = sts_button,
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
        """Apply theme."""
        self._tokens = tokens
        self._apply_style()

    def _apply_style(self):
        """Apply style."""
        self.setStyleSheet("QWidget { background: transparent; border: none; }")

    def set_has_text(self, has_text: bool):
        """Toggle send vs speech-to-speech button."""
        self._pill.set_has_text(has_text)

    def set_busy(self, busy: bool):
        """Set busy."""
        self.input_field.setEnabled(not busy)
        self.input_field.setPlaceholderText(
            "Quacky is thinking\u2026" if busy else "Message Quacky\u2026"
        )
        if not busy:
            self.input_field.setFocus()

    def clear(self):
        """Clear temporary state."""
        self.input_field.clear()

    def text(self) -> str:
        """Handle text."""
        return self.input_field.toPlainText()

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
