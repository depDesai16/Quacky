"""
widgets/chat_timeline.py — ChatTimeline

Layout:
  QScrollArea (widgetResizable=True)
    └── _container  (fills viewport; HBox: [stretch][_msg_col fixed-w][stretch])
         └── _msg_col  (centered message column, width from viewport)
              └── QVBoxLayout  [rows…][stretch]

Cross-platform alignment fix:
  Every message row (outer QWidget) gets setFixedWidth(_row_width()).
  This is the single source of truth for layout width — Qt cannot
  override it based on platform font metrics, DPI, or scrollbar style.

  _row_width() = _current_col_w - 2 * MSG_COL_SIDE_PAD

  Bubbles inside rows use setFixedWidth (see message_bubble.py).
  On window resize, _relayout_rows() updates every tracked row width
  alongside the existing bubble relayout.

  User row:      [stretch] [bubble fixed_w]   → right-aligned, consistent
  Assistant row: [bubble fixed_w] [stretch]   → left-aligned, consistent
"""

import time

from PyQt6.QtGui     import QColor
from PyQt6.QtCore    import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                              QEvent, QAbstractAnimation)
from PyQt6.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QSizePolicy, QFrame,
                              QGraphicsDropShadowEffect)

from theme            import ThemeManager, FONT_STACK
from .message_bubble  import (UserBubble, AssistantBubble, SystemMessage,
                               StreamingAssistantBubble, animate_in_widget)
from .thinking_bubble import ThinkingBubble
from .empty_state     import EmptyState

GROUP_SEC           = 60
NEAR_BOTTOM_THRESHOLD_PX = 24
AVATAR_W            = 28
AVATAR_GAP          = 8
COL_MIN_W           = 320
COL_MAX_W           = 920
BOTTOM_SAFE_PX      = 18
MSG_COL_SIDE_PAD    = 10
MSG_GROUP_GAP       = 14
MSG_CONT_GAP        = 4
ROW_LABEL_GAP       = 4
USER_BUBBLE_MAX_RATIO  = 0.78
USER_BUBBLE_MAX_CAP    = 520
ASST_BUBBLE_MAX_RATIO  = 0.88
ASST_BUBBLE_MAX_CAP    = 660
ROW_APPEAR_MS       = 180
SCROLL_MIN_MS       = 140
SCROLL_MAX_MS       = 320
SCROLL_DIST_FACTOR  = 0.50



class _NewMessagesPill(QPushButton):
    """
    Centered scroll-to-bottom indicator.
    Transparent by default; fills only on interaction.
    """
    def __init__(self, tokens: dict, parent: QWidget):
        super().__init__("↓  New messages", parent)
        self._tokens    = tokens
        self._clearance = 0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setMinimumWidth(132)
        self.setAutoDefault(False)
        self.hide()

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(18)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(0, 0, 0, 78))
        self.setGraphicsEffect(self._shadow)
        self._apply_style()

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(
            "QPushButton {"
            " background: transparent;"
            " color: " + t["newmsg.idle.fg"] + ";"
            " border: 1px solid " + t["newmsg.idle.border"] + ";"
            " border-radius: 17px;"
            " font-family: " + FONT_STACK + "; font-size: 12px; font-weight: 700;"
            " letter-spacing: 0.2px; padding: 0 18px;"
            " outline: none;"
            "}"
            " QPushButton:hover, QPushButton:focus {"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 " + t["newmsg.bg.top.hover"] + ","
            " stop:1 " + t["newmsg.bg.bottom.hover"] + ");"
            " color: " + t["newmsg.fg"] + ";"
            " border: 1px solid " + t["newmsg.border.hover"] + ";"
            "}"
            " QPushButton:pressed {"
            " background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            " stop:0 " + t["newmsg.bg.top.pressed"] + ","
            " stop:1 " + t["newmsg.bg.bottom.pressed"] + ");"
            " color: " + t["newmsg.fg"] + ";"
            " border: 1px solid " + t["newmsg.border"] + ";"
            "}"
        )

    def set_bottom_clearance(self, px: int):
        self._clearance = max(0, int(px))
        if self.isVisible():
            self._reposition()

    def show_pill(self):
        self.adjustSize()
        self._reposition()
        self.raise_()
        self.show()

    def hide_pill(self):
        self.hide()

    def _set_shadow_active(self, active: bool):
        if active:
            self._shadow.setBlurRadius(24)
            self._shadow.setOffset(0, 5)
            self._shadow.setColor(QColor(0, 0, 0, 106))
        else:
            self._shadow.setBlurRadius(18)
            self._shadow.setOffset(0, 4)
            self._shadow.setColor(QColor(0, 0, 0, 78))

    def enterEvent(self, event):
        self._set_shadow_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_shadow_active(self.hasFocus())
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self._set_shadow_active(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._set_shadow_active(False)
        super().focusOutEvent(event)

    def _reposition(self):
        vp = self.parent()
        if not vp:
            return
        pw, ph = vp.width(), vp.height()
        self.adjustSize()
        self.move((pw - self.width()) // 2,
                  ph - self.height() - 16 - self._clearance)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_style()



class ChatTimeline(QScrollArea):

    def __init__(self, draw_icon_fn, parent=None):
        super().__init__(parent)
        self._tokens               = ThemeManager.tokens()
        self._icon_fn              = draw_icon_fn
        self._messages             = []
        self._thinking_row         = None
        self._empty_widget         = None
        self._streaming_bubble     = None
        self._streaming_row        = None
        self._user_scrolled_up     = False
        self._all_bubbles          = []
        self._theme_widgets        = []
        self._sender_labels        = []
        self._stretch_added        = False
        self._current_col_w        = COL_MIN_W
        self._scroll_anim          = None
        self._user_dragging_scroll = False
        self._user_wheeling        = False
        self._last_scroll_value    = 0
        self._row_widgets          = []
        self._bottom_clearance     = BOTTOM_SAFE_PX

        self._msg_col = QWidget()
        self._msg_col.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        self._msg_col.setStyleSheet("background: transparent;")
        self._msg_col.setFixedWidth(COL_MIN_W)

        self._msg_layout = QVBoxLayout(self._msg_col)
        self._msg_layout.setContentsMargins(
            MSG_COL_SIDE_PAD, 18, MSG_COL_SIDE_PAD, self._bottom_clearance
        )
        self._msg_layout.setSpacing(0)

        self._empty_widget = EmptyState(self._tokens, icon_fn=self._icon_fn)
        self._msg_layout.addWidget(self._empty_widget)

        self._container = QWidget()
        self._container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._container.setStyleSheet("background: transparent;")

        h_lay = QHBoxLayout(self._container)
        h_lay.setContentsMargins(0, 0, 0, 0)
        h_lay.setSpacing(0)
        h_lay.addStretch(1)
        h_lay.addWidget(self._msg_col, 0)
        h_lay.addStretch(1)

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._pill = _NewMessagesPill(self._tokens, self.viewport())
        self._pill.clicked.connect(self._on_pill_clicked)
        self.viewport().installEventFilter(self)

        sb = self.verticalScrollBar()
        sb.valueChanged.connect(self._on_scroll_value)
        sb.rangeChanged.connect(self._on_scroll_range_changed)
        sb.sliderPressed.connect(self._on_scroll_slider_pressed)
        sb.sliderReleased.connect(self._on_scroll_slider_released)
        self._last_scroll_value = sb.value()

        self._apply_style()
        ThemeManager.subscribe(self.apply_theme)
        QTimer.singleShot(0, self._apply_column_width)


    # ------------------------------------------------------------------ public

    def add_user_message(self, text: str):
        self._refresh_column_width_if_ready()
        self._hide_empty()
        ts   = time.time()
        cont = self._is_continuation("user", ts)
        row  = self._build_user_row(text, cont)
        self._insert(row, gap=MSG_CONT_GAP if cont else MSG_GROUP_GAP)
        animate_in_widget(row, ROW_APPEAR_MS)
        self._messages.append(("user", ts))
        self._after_insert()

    def add_assistant_message(self, text: str):
        self._refresh_column_width_if_ready()
        self._hide_empty()
        self.hide_thinking()
        ts   = time.time()
        cont = self._is_continuation("asst", ts)
        row  = self._build_asst_row(text, cont)
        self._insert(row, gap=MSG_CONT_GAP if cont else MSG_GROUP_GAP)
        animate_in_widget(row, ROW_APPEAR_MS)
        self._messages.append(("asst", ts))
        self._after_insert()

    def add_system_message(self, html_text: str):
        row = SystemMessage(html_text, self._tokens)
        self._track_theme_widget(row)
        self._insert(row, gap=6)
        self._after_insert()

    def show_thinking(self):
        if self._thinking_row is not None:
            return
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        self._track_row_widget(row)
        rl  = QHBoxLayout(row)
        rl.setContentsMargins(0, 4, 0, 4)
        rl.setSpacing(0)
        thinking = ThinkingBubble(self._tokens)
        self._track_theme_widget(thinking)
        rl.addWidget(thinking)
        rl.addStretch(1)
        self._thinking_row = row
        self._insert(row, gap=6)
        self._after_insert()

    def hide_thinking(self):
        if self._thinking_row is None:
            return
        idx = self._msg_layout.indexOf(self._thinking_row)
        if idx >= 0:
            self._msg_layout.removeWidget(self._thinking_row)
        if self._thinking_row in self._row_widgets:
            self._row_widgets.remove(self._thinking_row)
        self._thinking_row.deleteLater()
        self._thinking_row = None

    def append_stream_chunk(self, chunk: str):
        self._refresh_column_width_if_ready()
        self._hide_empty()
        if self._streaming_bubble is None:
            self.hide_thinking()
            ts   = time.time()
            cont = self._is_continuation("asst", ts)
            bmax = self._bubble_max_asst()
            self._streaming_bubble = StreamingAssistantBubble(self._tokens)
            self._streaming_bubble.set_max_width(bmax)
            self._all_bubbles.append(self._streaming_bubble)
            self._track_theme_widget(self._streaming_bubble)
            row  = self._build_asst_bubble_row(self._streaming_bubble, cont)
            self._streaming_row = row
            self._insert(row, gap=MSG_CONT_GAP if cont else MSG_GROUP_GAP)
            animate_in_widget(row, ROW_APPEAR_MS)
            self._messages.append(("asst", ts))

        self._streaming_bubble.append_chunk(chunk)
        self._after_insert()

    def finalize_stream(self):
        if self._streaming_bubble is not None:
            self._streaming_bubble.finalize()
            self._streaming_bubble = None
            self._streaming_row    = None
            self._after_insert()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._pill.apply_theme(tokens)
        self._apply_style()
        if self._empty_widget is not None and hasattr(self._empty_widget, "apply_theme"):
            self._empty_widget.apply_theme(tokens)
        self._apply_sender_label_theme()
        self._apply_row_widget_theme()

    def scroll_to_bottom(self):
        QTimer.singleShot(16, self._smooth_scroll_to_bottom)

    def set_bottom_clearance(self, px: int):
        bottom = max(BOTTOM_SAFE_PX, int(px))
        if bottom == self._bottom_clearance:
            return
        self._bottom_clearance = bottom
        left, top, right, _ = self._msg_layout.getContentsMargins()
        self._msg_layout.setContentsMargins(left, top, right, bottom)
        self._msg_col.updateGeometry()
        self._container.updateGeometry()
        QTimer.singleShot(0, self._ensure_bottom_visible_after_layout)

    def set_new_message_pill_clearance(self, px: int):
        self._pill.set_bottom_clearance(px)


    # ----------------------------------------------------------------- builders

    def _hide_empty(self):
        if self._empty_widget is None:
            return
        self._msg_layout.removeWidget(self._empty_widget)
        self._empty_widget.deleteLater()
        self._empty_widget = None
        if not self._stretch_added:
            self._msg_layout.addStretch()
            self._stretch_added = True

    def _build_user_row(self, text: str, is_continuation: bool) -> QWidget:
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._track_row_widget(outer)

        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(ROW_LABEL_GAP)

        if not is_continuation:
            name = QLabel("You")
            name.setAlignment(Qt.AlignmentFlag.AlignRight)
            name.setStyleSheet(self._sender_css())
            self._sender_labels.append(name)
            ol.addWidget(name)

        bmax   = self._bubble_max_user()
        bubble = UserBubble(text, self._tokens)
        bubble.set_max_width(bmax)
        self._all_bubbles.append(bubble)
        self._track_theme_widget(bubble)

        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addStretch()
        hl.addWidget(bubble)
        ol.addLayout(hl)
        return outer

    def _build_asst_row(self, text: str, is_continuation: bool) -> QWidget:
        bmax   = self._bubble_max_asst()
        bubble = AssistantBubble(text, self._tokens)
        bubble.set_max_width(bmax)
        self._all_bubbles.append(bubble)
        self._track_theme_widget(bubble)
        return self._build_asst_bubble_row(bubble, is_continuation)

    def _build_asst_bubble_row(self, bubble: QWidget,
                                is_continuation: bool) -> QWidget:
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._track_row_widget(outer)

        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(ROW_LABEL_GAP)

        if not is_continuation:
            name_row = QHBoxLayout()
            name_row.setContentsMargins(0, 0, 0, 0)
            name_row.setSpacing(0)
            lbl = QLabel("Quacky")
            lbl.setStyleSheet(self._sender_css())
            self._sender_labels.append(lbl)
            name_row.addWidget(lbl)
            name_row.addStretch(1)
            ol.addLayout(name_row)

        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(bubble)
        hl.addStretch(1)
        ol.addLayout(hl)
        return outer


    # ----------------------------------------------------------------- layout helpers

    def _bubble_max_user(self) -> int:
        usable = max(1, self._current_col_w - 2 * MSG_COL_SIDE_PAD)
        return min(int(usable * USER_BUBBLE_MAX_RATIO), USER_BUBBLE_MAX_CAP)

    def _bubble_max_asst(self) -> int:
        usable = max(1, self._current_col_w - 2 * MSG_COL_SIDE_PAD)
        return min(int(usable * ASST_BUBBLE_MAX_RATIO), ASST_BUBBLE_MAX_CAP)

    def _row_width(self) -> int:
        return max(1, self._current_col_w - 2 * MSG_COL_SIDE_PAD)

    def _col_width_from_viewport(self, viewport_width: int) -> int:
        if viewport_width <= 0:
            return self._current_col_w
        max_allowed = min(COL_MAX_W, viewport_width)
        min_allowed = min(COL_MIN_W, max_allowed)
        return max(min(viewport_width, max_allowed), min_allowed)

    def _insert(self, widget: QWidget, gap: int = 0):
        if self._stretch_added:
            idx = self._msg_layout.count() - 1
        else:
            idx = self._msg_layout.count()
        if gap > 0:
            spacer = QWidget()
            spacer.setFixedHeight(gap)
            spacer.setStyleSheet("background: transparent;")
            self._msg_layout.insertWidget(idx, spacer)
            idx += 1
        self._msg_layout.insertWidget(idx, widget)

    def _is_continuation(self, sender: str, ts: float) -> bool:
        if not self._messages:
            return False
        ls, lt = self._messages[-1]
        return ls == sender and (ts - lt) < GROUP_SEC

    def _track_theme_widget(self, widget: QWidget):
        self._theme_widgets.append(widget)

    def _track_row_widget(self, row: QWidget):
        row.setFixedWidth(self._row_width())
        self._row_widgets.append(row)

    def _apply_sender_label_theme(self):
        dead = []
        css = self._sender_css()
        for lbl in self._sender_labels:
            try:
                lbl.setStyleSheet(css)
            except RuntimeError:
                dead.append(lbl)
        for d in dead:
            self._sender_labels.remove(d)

    def _apply_row_widget_theme(self):
        dead = []
        for w in self._theme_widgets:
            try:
                if hasattr(w, "apply_theme"):
                    w.apply_theme(self._tokens)
            except RuntimeError:
                dead.append(w)
        for d in dead:
            self._theme_widgets.remove(d)


    # ----------------------------------------------------------------- resize / scroll

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._apply_column_width)

    def wheelEvent(self, event):
        # Track wheel-originated movement so _on_scroll_value can distinguish
        # user intent from passive geometry/layout scrollbar updates.
        self._user_wheeling = True
        try:
            super().wheelEvent(event)
        finally:
            QTimer.singleShot(0, self._clear_user_wheeling)

    def _clear_user_wheeling(self):
        self._user_wheeling = False

    def eventFilter(self, obj, event):
        if obj is self.viewport() and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        ):
            QTimer.singleShot(0, self._apply_column_width)
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_column_width)
        QTimer.singleShot(30, self._apply_column_width)

    def _refresh_column_width_if_ready(self):
        vpw = self.viewport().width()
        if vpw <= 0:
            return
        self._apply_column_width()

    def _apply_column_width(self):
        col_w = self._col_width_from_viewport(self.viewport().width())
        width_changed = not (
            col_w == self._current_col_w and self._msg_col.width() == col_w
        )
        if width_changed:
            self._current_col_w = col_w
            self._msg_col.setFixedWidth(col_w)
            self._container.updateGeometry()
            self._relayout_rows()
            self._relayout_bubbles()

        if self._pill.isVisible():
            self._pill._reposition()

        self._ensure_bottom_visible_after_layout()

    def _on_scroll_range_changed(self, _min_value: int, _max_value: int):
        QTimer.singleShot(0, self._apply_column_width)
        if not self._user_scrolled_up and not self._user_dragging_scroll:
            QTimer.singleShot(0, self._snap_to_bottom_if_needed)
            QTimer.singleShot(60, self._snap_to_bottom_if_needed)

    def _relayout_bubbles(self):
        bmax_user = self._bubble_max_user()
        bmax_asst = self._bubble_max_asst()
        dead = []
        for b in self._all_bubbles:
            try:
                if isinstance(b, UserBubble):
                    b.set_max_width(bmax_user)
                else:
                    b.set_max_width(bmax_asst)
            except RuntimeError:
                dead.append(b)
        for d in dead:
            self._all_bubbles.remove(d)

    def _relayout_rows(self):
        row_w = self._row_width()
        dead = []
        for row in self._row_widgets:
            try:
                row.setFixedWidth(row_w)
                row.updateGeometry()
            except RuntimeError:
                dead.append(row)
        for d in dead:
            self._row_widgets.remove(d)

    def _ensure_bottom_visible_after_layout(self):
        if self._user_scrolled_up or self._user_dragging_scroll:
            return
        QTimer.singleShot(0, self._snap_to_bottom_if_needed)

    def _snap_to_bottom_if_needed(self):
        if self._user_scrolled_up or self._user_dragging_scroll:
            return
        sb = self.verticalScrollBar()
        if sb.isSliderDown():
            return
        if (sb.maximum() - sb.value()) <= 2:
            sb.setValue(sb.maximum())
            return
        self._smooth_scroll_to_bottom()

    def _smooth_scroll_to_bottom(self):
        if self._user_dragging_scroll:
            return
        sb = self.verticalScrollBar()
        target  = sb.maximum()
        current = sb.value()
        dist    = target - current
        if dist <= 0:
            return
        if dist < 6:
            sb.setValue(target)
            return

        self._ensure_scroll_anim()
        anim = self._scroll_anim
        if anim is None:
            sb.setValue(target)
            return

        duration = max(SCROLL_MIN_MS, min(SCROLL_MAX_MS, int(dist * SCROLL_DIST_FACTOR)))

        if anim.state() == QAbstractAnimation.State.Running:
            anim.stop()
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    def _ensure_scroll_anim(self):
        if self._scroll_anim is not None:
            return
        sb   = self.verticalScrollBar()
        anim = QPropertyAnimation(sb, b"value", self)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_anim = anim

    def _is_scroll_animating(self) -> bool:
        return (
            self._scroll_anim is not None and
            self._scroll_anim.state() == QAbstractAnimation.State.Running
        )

    def _stop_scroll_animation(self):
        if self._scroll_anim is not None and self._is_scroll_animating():
            self._scroll_anim.stop()

    def _after_insert(self):
        QTimer.singleShot(30, self._do_scroll_check)
        # Rich-text layout can finalize a bit later on some platforms.
        QTimer.singleShot(140, self._do_scroll_check)

    def _do_scroll_check(self):
        self._container.updateGeometry()
        if self._user_dragging_scroll:
            return
        if not self._user_scrolled_up:
            if self._is_scroll_animating():
                self._smooth_scroll_to_bottom()
                return
            self._smooth_scroll_to_bottom()
            QTimer.singleShot(90, self._snap_to_bottom_if_needed)
        else:
            if not self._pill.isVisible():
                self._pill.show_pill()
                self._pill._reposition()

    def _on_scroll_value(self, value: int):
        sb = self.verticalScrollBar()
        scrolling_up = value < self._last_scroll_value
        self._last_scroll_value = value
        manual_scroll = self._user_dragging_scroll or self._user_wheeling or sb.isSliderDown()

        if scrolling_up and manual_scroll and sb.maximum() > 0:
            self._user_scrolled_up = True
            self._stop_scroll_animation()
            if not self._pill.isVisible():
                self._pill.show_pill()
                self._pill._reposition()
            return

        near_bottom = (sb.maximum() - value) <= self._near_bottom_threshold(sb)
        if near_bottom:
            if self._user_scrolled_up:
                self._user_scrolled_up = False
                if self._pill.isVisible():
                    self._pill.hide_pill()
            return

        # Do not mark scrolled-up on passive geometry changes.
        # Content growth after rendering can raise max() and briefly move us
        # away from bottom without any user intent.
        if manual_scroll and sb.maximum() > 0:
            self._user_scrolled_up = True

    def _on_pill_clicked(self):
        self._user_scrolled_up = False
        self._pill.hide_pill()
        self._smooth_scroll_to_bottom()

    def _near_bottom_threshold(self, sb) -> int:
        return 0 if sb.maximum() <= 0 else NEAR_BOTTOM_THRESHOLD_PX

    def _on_scroll_slider_pressed(self):
        self._user_dragging_scroll = True
        self._stop_scroll_animation()

    def _on_scroll_slider_released(self):
        self._user_dragging_scroll = False
        self._last_scroll_value = self.verticalScrollBar().value()
        self._on_scroll_value(self.verticalScrollBar().value())


    # ----------------------------------------------------------------- style

    def _sender_css(self) -> str:
        t = self._tokens
        return (f"font-family:{FONT_STACK}; font-size:11px; font-weight:700;"
                f"letter-spacing:0.4px;"
                f"color:{t['text.secondary']}; background:transparent; border:none;")

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 9px;
                margin: 0px 1px 0px 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar.thumb']};
                border: none;
                border-radius: 5px;
                min-height: 28px;
                margin: 0px 1px 0px 1px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['scrollbar.hover']};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: {t['scrollbar.track']};
                border: none;
                border-radius: 5px;
                margin: 0px 1px 0px 1px;
            }}
        """)
        self._msg_col.setStyleSheet("background: transparent;")

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self.apply_theme)
        except Exception:
            pass
