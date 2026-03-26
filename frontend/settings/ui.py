
import math as _math

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSignalBlocker, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)
from theme import FONT_FAMILY_UI, FONT_STACK, ThemeManager
from widgets.card_widget import CardWidget

from .widgets.toggle_slider import ToggleSlider

SETTINGS_METRICS: dict = {
    "sidebar_width": 164,
    "sidebar_top_pad": 20,
    "sidebar_bottom_pad": 20,
    "content_pad_x": 26,
    "content_pad_y": 24,
    "section_gap": 16,
    "card_radius": 14,
    "card_pad_x": 16,
    "card_pad_y": 12,
    "row_min_h": 64,
    "row_inner_vpad": 10,
    "row_gap": 12,
    "row_control_col_w": 196,
    "row_control_wide_w": 332,
    "control_h": 36,
    "action_btn_h": 34,
    "panel_inset": 1,
    "tab_h": 44,
}
_BASE_SETTINGS_METRICS = SETTINGS_METRICS.copy()




class _SettingsTabButton(QWidget):

    clicked = pyqtSignal()

    _ICONS = ("features", "appearance", "apikey", "security")

    def __init__(self, label: str, icon_key: str, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._label    = label
        self._icon_key = icon_key
        self._active   = False
        self._hovered  = False
        self._tokens   = ThemeManager.tokens()

        self.setFixedHeight(SETTINGS_METRICS["tab_h"])
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        ThemeManager.subscribe(self._on_theme)

    def _on_theme(self, tokens):
        """Handle theme callbacks."""
        self._tokens = tokens
        self.update()

    def set_active(self, active: bool):
        """Set active."""
        self._active = active
        self.update()

    def enterEvent(self, e):
        """Handle the enter event."""
        self._hovered = True;  self.update()

    def leaveEvent(self, e):
        """Handle the leave event."""
        self._hovered = False; self.update()

    def mousePressEvent(self, e):
        """Handle the mousepress event."""
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _event):
        """Handle the paint event."""
        t   = self._tokens
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())

        if self._active:
            bg = QColor(t["accent.primary"])
            bg.setAlphaF(0.10)
            p.fillRect(QRectF(0, 0, w, h), bg)
        elif self._hovered:
            bg = QColor(t["bg.elevated"])
            bg.setAlphaF(0.70)
            p.fillRect(QRectF(0, 0, w, h), bg)

        if self._active:
            bar = QColor(t["accent.primary"])
            p.fillRect(QRectF(1, 0, 2, h), bar)

        icon_x = 18.0
        icon_y = (h - 18.0) / 2.0
        icon_color = (QColor(t["accent.primary"]) if self._active
                      else QColor(t["text.secondary"] if self._hovered
                                  else t["text.muted"]))
        self._draw_icon(p, icon_x, icon_y, 18.0, icon_color)

        text_color = (QColor(t["text.primary"]) if self._active
                      else QColor(t["text.secondary"]))
        p.setPen(text_color)
        from PyQt6.QtGui import QFont as _QFont
        app_font = QApplication.font()
        font = _QFont(app_font.family() or FONT_FAMILY_UI)
        font.setPixelSize(13)
        font.setWeight(_QFont.Weight.DemiBold if self._active
                       else _QFont.Weight.Normal)
        p.setFont(font)
        p.drawText(
            QRectF(icon_x + 26, 0, w - icon_x - 26 - 8, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label,
        )
        p.end()

    def _draw_icon(self, p: QPainter, x: float, y: float,
                   size: float, color: QColor):
        """Handle draw icon."""
        pen = QPen(color, 1.4, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx = x + size / 2
        cy = y + size / 2
        s  = size

        if self._icon_key == "features":
            cell = s * 0.36
            gap  = s * 0.10
            for ri in range(2):
                for ci in range(2):
                    rx = x + ci * (cell + gap)
                    ry = y + ri * (cell + gap) + (s - 2 * cell - gap) / 2
                    path = QPainterPath()
                    path.addRoundedRect(QRectF(rx, ry, cell, cell), 2.0, 2.0)
                    p.drawPath(path)

        elif self._icon_key == "appearance":
            r_disc = s * 0.18
            p.drawEllipse(QRectF(cx - r_disc, cy - r_disc,
                                  r_disc * 2, r_disc * 2))
            for i in range(6):
                angle = _math.radians(i * 60)
                r1 = s * 0.29
                r2 = s * 0.40
                p.drawLine(
                    QPointF(cx + r1 * _math.cos(angle),
                             cy + r1 * _math.sin(angle)),
                    QPointF(cx + r2 * _math.cos(angle),
                             cy + r2 * _math.sin(angle)),
                )

        elif self._icon_key == "apikey":
            bow_r = s * 0.22
            bx = x + bow_r + s * 0.04
            by = cy
            p.drawEllipse(QRectF(bx - bow_r, by - bow_r,
                                  bow_r * 2, bow_r * 2))
            shaft_x1 = bx + bow_r
            shaft_x2 = x + s - s * 0.06
            shaft_y = cy
            p.drawLine(QPointF(shaft_x1, shaft_y),
                       QPointF(shaft_x2, shaft_y))
            tooth_h = s * 0.14
            for tx in (shaft_x1 + (shaft_x2 - shaft_x1) * 0.45,
                       shaft_x1 + (shaft_x2 - shaft_x1) * 0.68):
                p.drawLine(QPointF(tx, shaft_y),
                           QPointF(tx, shaft_y + tooth_h))

        elif self._icon_key == "security":
            path = QPainterPath()
            top = y + s * 0.05
            bot = y + s * 0.92
            half = s * 0.38
            path.moveTo(QPointF(cx, top))
            path.lineTo(QPointF(cx + half, top + s * 0.14))
            path.lineTo(QPointF(cx + half, cy + s * 0.05))
            path.quadTo(QPointF(cx + half, bot), QPointF(cx, bot))
            path.quadTo(QPointF(cx - half, bot), QPointF(cx - half, cy + s * 0.05))
            path.lineTo(QPointF(cx - half, top + s * 0.14))
            path.closeSubpath()
            p.drawPath(path)

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass


class _SettingsCard(QWidget):

    def __init__(self, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self.setObjectName("settingsCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._row_count = 0

        pad_x = SETTINGS_METRICS["card_pad_x"]
        pad_y = SETTINGS_METRICS["card_pad_y"]
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(pad_x, pad_y, pad_x, pad_y)
        self._lay.setSpacing(0)

    def add_row(self, row: QWidget):
        """Add row."""
        if self._row_count > 0:
            div = QWidget(self)
            div.setObjectName("settingsCardRowDivider")
            div.setFixedHeight(1)
            self._lay.addWidget(div)
        self._lay.addWidget(row)
        self._row_count += 1

    def add_widget(self, widget: QWidget):
        """Add widget."""
        self._lay.addWidget(widget)


class _SettingsRow(QWidget):

    def __init__(self, label_text: str, subtitle: str, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self.setObjectName("settingsRow")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setMinimumHeight(SETTINGS_METRICS["row_min_h"])

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, SETTINGS_METRICS["row_inner_vpad"], 0, SETTINGS_METRICS["row_inner_vpad"])
        lay.setSpacing(SETTINGS_METRICS["row_gap"])
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel(label_text)
        self.title.setObjectName("settingsRowLabel")
        self.title.setWordWrap(True)
        text_col.addWidget(self.title)

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("settingsRowSub")
        self.subtitle.setWordWrap(True)
        text_col.addWidget(self.subtitle)

        self._control_host = QWidget(self)
        self._control_host.setObjectName("settingsRowControlHost")
        self._control_host.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        host_lay = QHBoxLayout(self._control_host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(0)
        host_lay.addStretch(1)

        lay.addLayout(text_col, 1)
        lay.addWidget(self._control_host, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_control(self, control: QWidget, width: int | None = None):
        """Set control."""
        if width is None:
            width = SETTINGS_METRICS["row_control_col_w"]
        self._control_host.setFixedWidth(width)
        host_lay = self._control_host.layout()
        while host_lay.count() > 1:
            item = host_lay.takeAt(1)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        host_lay.addWidget(control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


class _ModeComboDelegate(QStyledItemDelegate):

    def __init__(self, combo: QComboBox, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._combo = combo
        self._tokens = ThemeManager.tokens()
        ThemeManager.subscribe(self._on_theme)
        combo.currentIndexChanged.connect(self._refresh_view)

    def _refresh_view(self, *_args):
        """Handle refresh view."""
        view = self._combo.view()
        if view is not None and view.viewport() is not None:
            view.viewport().update()

    def _on_theme(self, tokens: dict):
        """Handle theme callbacks."""
        self._tokens = tokens
        self._refresh_view()

    def paint(self, painter: QPainter, option, index):
        """Handle paint."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_light = ThemeManager.current() == "light"
        row_rect = QRectF(option.rect).adjusted(6.0, 2.0, -6.0, -2.0)
        is_current = index.row() == self._combo.currentIndex()
        is_hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        bg = None
        if is_current:
            bg = QColor(self._tokens["text.primary"])
            bg.setAlphaF(0.14 if is_light else 0.20)
        elif is_hovered:
            bg = QColor(self._tokens["text.primary"])
            bg.setAlphaF(0.06 if is_light else 0.11)

        if bg is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(row_rect, 8.0, 8.0)

        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        text_rect = row_rect.adjusted(12.0, 0.0, -30.0, 0.0).toRect()
        painter.setPen(QColor(self._tokens["text.primary"]))
        app_font = QApplication.font()
        font = QFont(app_font.family() or FONT_FAMILY_UI)
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )

        if is_current:
            pen = QPen(
                QColor(self._tokens["text.primary"]),
                1.7,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
            painter.setPen(pen)
            cy = row_rect.center().y()
            x2 = row_rect.right() - 11.0
            xm = x2 - 4.0
            x1 = xm - 3.2
            painter.drawLine(QPointF(x1, cy), QPointF(xm, cy + 3.0))
            painter.drawLine(QPointF(xm, cy + 3.0), QPointF(x2, cy - 4.0))

        painter.restore()

    def sizeHint(self, option, index):
        """Handle sizehint."""
        size = super().sizeHint(option, index)
        size.setHeight(34)
        return size

    def dispose(self):
        """Handle dispose."""
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass

    def __del__(self):
        """Release resources during object cleanup."""
        self.dispose()


class _ModeComboBox(QComboBox):

    def __init__(self, parent=None):
        """Initialize the instance state."""
        super().__init__(parent)
        self._tokens = ThemeManager.tokens()
        self.setFrame(False)
        ThemeManager.subscribe(self._on_theme)

    def _on_theme(self, tokens: dict):
        """Handle theme callbacks."""
        self._tokens = tokens
        self.apply_theme(tokens)

    def apply_theme(self, tokens: dict):
        """Apply theme."""
        self._tokens = tokens
        t = tokens
        card_bg      = t.get("settings.bg.card",       t["bg.elevated"])
        input_bg     = t.get("settings.bg.input",       t["bg.elevated"])
        border       = t.get("settings.border.strong",  t["border.strong"])
        text         = t["text.primary"]
        accent       = t["accent.primary"]
        font         = FONT_STACK
        h            = SETTINGS_METRICS["control_h"]

        self.setStyleSheet(f"""
            QComboBox {{
                font-family: {font};
                font-size: 13px;
                font-weight: 500;
                color: {text};
                background: {input_bg};
                border: 1px solid {border};
                border-radius: 9px;
                padding: 0 28px 0 10px;
                min-height: {h}px;
            }}
            QComboBox:hover {{
                border: 1px solid {t["text.secondary"]};
            }}
            QComboBox:on, QComboBox:focus {{
                border: 1px solid {accent};
            }}
            QComboBox::drop-down {{
                width: 22px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                font-family: {font};
                font-size: 13px;
                font-weight: 500;
                color: {text};
                background: {card_bg};
                border: 1px solid {border};
                padding: 4px;
                outline: 0;
                selection-background-color: transparent;
                selection-color: {text};
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 34px;
                padding: 0 12px;
                color: {text};
            }}
        """)
        self.update()

    def showPopup(self):
        """Handle showpopup."""
        super().showPopup()
        self._fix_popup()
        QTimer.singleShot(0, self._fix_popup)

    def _fix_popup(self):
        """Handle fix popup."""
        view  = self.view()
        popup = view.window() if view is not None else None
        if popup is None or popup is self:
            return

        t       = self._tokens
        card_bg = t.get("settings.bg.card",      t["bg.elevated"])
        border  = t.get("settings.border.strong", t["border.strong"])

        if isinstance(popup, QFrame):
            popup.setFrameShape(QFrame.Shape.NoFrame)
            popup.setLineWidth(0)
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        popup.setContentsMargins(6, 6, 6, 6)   # room for shadow + border-radius
        popup.setStyleSheet(
            f"QFrame {{"
            f"  background: {card_bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 10px;"
            f"  padding: 4px 0px;"
            f"}}"
            f"QAbstractScrollArea {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  border-radius: 0px;"
            f"  outline: none;"
            f"}}"
            f"QListView {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListView::item {{"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
        )

        gap     = 4
        g_pos   = self.mapToGlobal(QPoint(0, self.height() + gap))
        pop_w   = max(self.width() + 40, popup.width())
        pop_h   = popup.height()

        screen  = QApplication.screenAt(g_pos) or QApplication.primaryScreen()
        if screen:
            sg  = screen.availableGeometry()
            x   = max(sg.left(), min(g_pos.x(), sg.right() - pop_w))
            y   = g_pos.y()
            if y + pop_h > sg.bottom():
                y = max(sg.top(),
                        self.mapToGlobal(QPoint(0, -(pop_h + gap))).y())
        else:
            x, y = g_pos.x(), g_pos.y()

        popup.setFixedWidth(pop_w)
        popup.move(x, y)

    def paintEvent(self, event):
        """Handle the paint event."""
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(self._tokens["text.secondary"]), 1.6,
                   Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                   Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        cx = float(self.width() - 16)
        cy = float(self.height()) / 2.0 + 0.5
        p.drawLine(QPointF(cx - 4.0, cy - 2.0), QPointF(cx, cy + 2.0))
        p.drawLine(QPointF(cx, cy + 2.0), QPointF(cx + 4.0, cy - 2.0))
        p.end()

    def closeEvent(self, event):
        """Handle the close event."""
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass
        super().closeEvent(event)

    def __del__(self):
        """Release resources during object cleanup."""
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass


class _ApiKeyTestWorker(QThread):
    result_ready = pyqtSignal(bool, str)

    def __init__(self, client, api_key: str):
        """Initialize the instance state."""
        super().__init__()
        self._client = client
        self._api_key = api_key.strip()

    def run(self):
        """Execute the worker task."""
        if self._client is None:
            self.result_ready.emit(False, "Client unavailable for key test.")
            return
        result = self._client.test_api_key(self._api_key)
        if "error" in result:
            self.result_ready.emit(False, str(result["error"]))
            return
        ok = bool(result.get("ok"))
        message = str(result.get("message", "API key test completed."))
        self.result_ready.emit(ok, message)

class SettingsPanelMixin:
    def _sync_platform_metrics(self):
        """Tune settings layout metrics for current font metrics."""
        app = QApplication.instance()
        font = app.font() if app is not None else QFont(FONT_FAMILY_UI, 10)
        text_h = QFontMetrics(font).height()
        scale = max(0.95, min(1.25, text_h / 14.0))

        for key, value in _BASE_SETTINGS_METRICS.items():
            SETTINGS_METRICS[key] = max(1, int(round(value * scale)))
        SETTINGS_METRICS["panel_inset"] = _BASE_SETTINGS_METRICS["panel_inset"]

    def _build_settings_page(self) -> QWidget:
        """Build settings page."""
        self._sync_platform_metrics()
        page = QWidget()
        page.setObjectName("settingsPage")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QHBoxLayout(page)
        inset = SETTINGS_METRICS["panel_inset"]
        outer.setContentsMargins(inset, 0, inset, inset)
        outer.setSpacing(0)

        self._settings_sidebar = QWidget()
        self._settings_sidebar.setObjectName("settingsSidebar")
        self._settings_sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._settings_sidebar.setFixedWidth(SETTINGS_METRICS["sidebar_width"])
        sb_layout = QVBoxLayout(self._settings_sidebar)
        sb_layout.setContentsMargins(
            0,
            SETTINGS_METRICS["sidebar_top_pad"],
            0,
            SETTINGS_METRICS["sidebar_bottom_pad"],
        )
        sb_layout.setSpacing(2)

        tabs_meta = [
            ("Features", "features"),
            ("Appearance", "appearance"),
            ("API Key", "apikey"),
            ("Security", "security"),
        ]

        self._settings_tab_btns = []
        for label, icon_key in tabs_meta:
            btn = _SettingsTabButton(label, icon_key, parent=self._settings_sidebar)
            btn.clicked.connect(lambda _=None, k=icon_key: self._switch_settings_tab(k))
            sb_layout.addWidget(btn)
            self._settings_tab_btns.append((icon_key, btn))
        sb_layout.addStretch(1)
        outer.addWidget(self._settings_sidebar)

        self._sidebar_divider = QWidget()
        self._sidebar_divider.setObjectName("settingsSidebarDivider")
        self._sidebar_divider.setFixedWidth(1)
        self._settings_dividers.append(self._sidebar_divider)
        outer.addWidget(self._sidebar_divider)

        self._settings_content = QWidget()
        self._settings_content.setObjectName("settingsContent")
        self._settings_content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_lay = QVBoxLayout(self._settings_content)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        self._settings_stack = QStackedWidget()
        self._settings_stack.setObjectName("settingsStack")
        self._settings_stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._settings_stack.addWidget(self._build_tab_features())
        self._settings_stack.addWidget(self._build_tab_appearance())
        self._settings_stack.addWidget(self._build_tab_apikey())
        self._settings_stack.addWidget(self._build_tab_security())
        content_lay.addWidget(self._settings_stack)
        outer.addWidget(self._settings_content, 1)

        self._switch_settings_tab("features")
        self._settings_container = page
        self._update_settings_theme(ThemeManager.tokens())
        return page

    def _build_tab_features(self) -> QWidget:
        """Build tab features."""
        page = self._make_content_page(
            "Features",
            "Control core assistant behavior and interaction defaults.",
        )
        lay = page.layout()

        card = _SettingsCard()
        self._settings_cards.append(card)
        lay.addWidget(card)

        row1, self._toggle_model = self._make_settings_toggle_row(
            "Model Visibility",
            "Show or hide the floating 3D model overlay.",
            bool(self.model_window and self.model_window.isVisible()),
        )
        self._toggle_model.toggled.connect(self.set_model_visible)
        card.add_row(row1)

        row2, self._toggle_sts = self._make_settings_toggle_row(
            "Speech-to-Speech",
            "Enable microphone input and voice responses.",
            bool(self.speechtospeech_enabled),
        )
        self._toggle_sts.toggled.connect(self.set_speechtospeech_enabled)
        card.add_row(row2)

        row3, self._toggle_timer_confirm = self._make_settings_toggle_row(
            "Confirm Timers/Alarms",
            "Ask for confirmation before setting or canceling timers and alarms.",
            bool(getattr(self, "timer_confirmation_enabled", True)),
        )
        self._toggle_timer_confirm.toggled.connect(
            self.set_timer_confirmation_enabled
        )
        card.add_row(row3)

        row4, self._toggle_open_app_confirm = self._make_settings_toggle_row(
            "Confirm App Opens",
            "Ask for confirmation before opening applications.",
            bool(getattr(self, "open_app_confirmation_enabled", True)),
        )
        self._toggle_open_app_confirm.toggled.connect(
            self.set_open_app_confirmation_enabled
        )
        card.add_row(row4)

        lay.addStretch(1)
        return page

    def _build_tab_appearance(self) -> QWidget:
        """Build tab appearance."""
        page = self._make_content_page(
            "Appearance",
            "Theme and visual presentation.",
        )
        lay = page.layout()

        card = _SettingsCard()
        self._settings_cards.append(card)
        lay.addWidget(card)

        row1, self._theme_mode_combo = self._make_settings_select_row(
            "Color Mode",
            "Choose Light, Dark, or follow your system setting.",
            [
                ("Light", "light"),
                ("Dark", "dark"),
                ("System", "system"),
            ],
            ThemeManager.preference(),
        )
        self._theme_mode_combo.currentIndexChanged.connect(
            self._on_settings_color_mode_changed
        )
        card.add_row(row1)

        lay.addStretch(1)
        return page

    def _build_tab_apikey(self) -> QWidget:
        """Build tab apikey."""
        page = self._make_content_page(
            "API Key",
            "Manage your Gemini API key for assistant requests.",
        )
        lay = page.layout()

        card = _SettingsCard()
        self._settings_cards.append(card)
        lay.addWidget(card)

        self._api_key_input = QLineEdit()
        self._api_key_input.setObjectName("settingsInput")
        self._api_key_input.setPlaceholderText("AIza...")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setMinimumHeight(SETTINGS_METRICS["control_h"])
        self._api_key_input.setMaximumHeight(SETTINGS_METRICS["control_h"])
        self._api_key_input.setText(getattr(self, "_saved_api_key", ""))
        self._api_key_input.textChanged.connect(self._update_api_key_action_state)
        self._settings_inputs.append(self._api_key_input)

        self._api_key_reveal_btn = QPushButton("Reveal")
        self._api_key_reveal_btn.setObjectName("settingsActionButton")
        self._api_key_reveal_btn.setProperty("role", "ghost")
        self._api_key_reveal_btn.setCheckable(True)
        self._api_key_reveal_btn.setMinimumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_reveal_btn.setMaximumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_reveal_btn.setMinimumWidth(84)
        self._api_key_reveal_btn.toggled.connect(self._on_toggle_api_key_reveal)
        self._settings_action_buttons.append(self._api_key_reveal_btn)

        key_controls = QWidget()
        key_controls_lay = QHBoxLayout(key_controls)
        key_controls_lay.setContentsMargins(0, 1, 0, 1)
        key_controls_lay.setSpacing(8)
        key_controls_lay.addWidget(self._api_key_input, 1)
        key_controls_lay.addWidget(self._api_key_reveal_btn, 0)

        key_row_widget = QWidget()
        key_row_widget.setObjectName("settingsRow")
        key_row_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        key_row_lay = QVBoxLayout(key_row_widget)
        key_row_lay.setContentsMargins(0, SETTINGS_METRICS["row_inner_vpad"],
                                       0, SETTINGS_METRICS["row_inner_vpad"])
        key_row_lay.setSpacing(8)
        _key_title = QLabel("Gemini 2.5 API Key")
        _key_title.setObjectName("settingsRowLabel")
        _key_sub = QLabel("Paste your key to enable assistant requests.")
        _key_sub.setObjectName("settingsRowSub")
        self._settings_row_labels.extend([_key_title, _key_sub])
        key_row_lay.addWidget(_key_title)
        key_row_lay.addWidget(_key_sub)
        key_row_lay.addWidget(key_controls)
        card.add_row(key_row_widget)

        self._api_key_save_btn = QPushButton("Save")
        self._api_key_save_btn.setObjectName("settingsActionButton")
        self._api_key_save_btn.setProperty("role", "primary")
        self._api_key_save_btn.setMinimumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_save_btn.setMaximumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_save_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._api_key_save_btn.clicked.connect(self._on_save_api_key_clicked)

        self._api_key_test_btn = QPushButton("Test Connection")
        self._api_key_test_btn.setObjectName("settingsActionButton")
        self._api_key_test_btn.setProperty("role", "secondary")
        self._api_key_test_btn.setMinimumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_test_btn.setMaximumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_test_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._api_key_test_btn.clicked.connect(self._on_test_api_key_clicked)

        self._api_key_remove_btn = QPushButton("Remove Key")
        self._api_key_remove_btn.setObjectName("settingsActionButton")
        self._api_key_remove_btn.setProperty("role", "danger")
        self._api_key_remove_btn.setMinimumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_remove_btn.setMaximumHeight(SETTINGS_METRICS["action_btn_h"])
        self._api_key_remove_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._api_key_remove_btn.clicked.connect(self._on_remove_api_key_clicked)

        for btn in (self._api_key_save_btn, self._api_key_test_btn, self._api_key_remove_btn):
            self._settings_action_buttons.append(btn)

        action_row_widget = QWidget()
        action_row_widget.setObjectName("settingsRow")
        action_row_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        action_row_lay = QVBoxLayout(action_row_widget)
        action_row_lay.setContentsMargins(0, SETTINGS_METRICS["row_inner_vpad"],
                                          0, SETTINGS_METRICS["row_inner_vpad"])
        action_row_lay.setSpacing(8)
        _act_title = QLabel("Actions")
        _act_title.setObjectName("settingsRowLabel")
        _act_sub = QLabel("Save locally, verify connectivity, or remove the stored key.")
        _act_sub.setObjectName("settingsRowSub")
        self._settings_row_labels.extend([_act_title, _act_sub])
        action_row_lay.addWidget(_act_title)
        action_row_lay.addWidget(_act_sub)
        action_btn_row = QWidget()
        action_btn_lay = QHBoxLayout(action_btn_row)
        action_btn_lay.setContentsMargins(0, 1, 0, 1)
        action_btn_lay.setSpacing(8)
        action_btn_row.setMinimumHeight(SETTINGS_METRICS["action_btn_h"] + 2)
        action_btn_lay.addWidget(self._api_key_save_btn, 1)
        action_btn_lay.addWidget(self._api_key_test_btn, 2)
        action_btn_lay.addWidget(self._api_key_remove_btn, 2)
        action_row_lay.addWidget(action_btn_row)
        card.add_row(action_row_widget)

        hint = QLabel(
            "Stored locally on this device. Test connection sends a one-time "
            "verification request to Google."
        )
        hint.setObjectName("settingsHint")
        hint.setWordWrap(True)
        self._settings_input_hints.append(hint)
        lay.addWidget(hint)
        self._update_api_key_action_state()

        lay.addStretch(1)
        return page

    def _build_tab_security(self) -> QWidget:
        """Build tab security."""
        page = self._make_content_page(
            "Security",
            "Privacy and safety controls for local usage.",
        )
        lay = page.layout()

        card = _SettingsCard()
        self._settings_cards.append(card)
        lay.addWidget(card)

        placeholder = QLabel("Additional security controls will appear in a future update.")
        placeholder.setObjectName("settingsHint")
        placeholder.setWordWrap(True)
        self._settings_row_labels.append(placeholder)
        card.add_widget(placeholder)

        lay.addStretch(1)
        return page

    def _make_content_page(self, title: str, subtitle: str) -> QWidget:
        """Build content page."""
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        inner.setObjectName("settingsContentInner")
        inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        inner.setStyleSheet("QWidget { background: transparent; }")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(
            SETTINGS_METRICS["content_pad_x"],
            SETTINGS_METRICS["content_pad_y"],
            SETTINGS_METRICS["content_pad_x"],
            SETTINGS_METRICS["content_pad_y"],
        )
        lay.setSpacing(SETTINGS_METRICS["section_gap"])

        heading = QLabel(title)
        heading.setObjectName("settingsHeading")
        heading.setWordWrap(True)
        self._settings_row_labels.append(heading)
        lay.addWidget(heading)

        heading_sub = QLabel(subtitle)
        heading_sub.setObjectName("settingsHeadingSub")
        heading_sub.setWordWrap(True)
        self._settings_row_labels.append(heading_sub)
        lay.addWidget(heading_sub)

        scroll.setWidget(inner)
        scroll._inner_layout = lay
        scroll.layout = lambda: lay  # type: ignore[method-assign]
        return scroll

    def _make_settings_control_row(self, label_text: str, subtitle: str,
                                   control: QWidget, control_width: int | None = None) -> _SettingsRow:
        """Build settings control row."""
        row = _SettingsRow(label_text, subtitle)
        self._settings_rows.append(row)
        self._settings_row_labels.extend([row.title, row.subtitle])
        row.set_control(control, control_width)
        return row

    def _make_settings_toggle_row(self, label_text: str, subtitle: str,
                                  initial: bool) -> tuple[_SettingsRow, ToggleSlider]:
        """Build settings toggle row."""
        toggle = ToggleSlider(checked=initial)
        row = self._make_settings_control_row(label_text, subtitle, toggle)
        return row, toggle

    def _make_settings_select_row(self, label_text: str,
                                  subtitle: str,
                                  options: list[tuple[str, str]],
                                  selected: str) -> tuple[_SettingsRow, QComboBox]:
        """Build settings select row."""
        combo = _ModeComboBox()
        combo.setObjectName("settingsRowCombo")
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.setFixedHeight(SETTINGS_METRICS["control_h"])
        combo.setMinimumWidth(120)

        combo_view = QListView(combo)
        combo_view.setObjectName("settingsRowComboView")
        combo_view.setSpacing(0)
        combo_view.setMouseTracking(True)
        combo_view.setUniformItemSizes(True)
        combo_view.setFrameShape(QFrame.Shape.NoFrame)
        combo_view.setContentsMargins(0, 0, 0, 0)
        combo_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        combo_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        combo.setView(combo_view)
        combo_view.setItemDelegate(_ModeComboDelegate(combo, combo_view))

        for text, value in options:
            combo.addItem(text, value)
        idx = combo.findData(selected)
        if idx >= 0:
            combo.setCurrentIndex(idx)

        combo.apply_theme(ThemeManager.tokens())

        self._settings_selects.append(combo)
        row = self._make_settings_control_row(label_text, subtitle, combo)
        return row, combo

    def _load_saved_api_key(self) -> str:
        """Load saved api key."""
        value = getattr(self, "_saved_api_key", "")
        key = str(value).strip() if value is not None else ""
        self._saved_api_key = key
        return key

    def _update_api_key_action_state(self, *_args):
        """Update api key action state."""
        key_text = self._api_key_input.text().strip() if self._api_key_input else ""
        saved = bool(getattr(self, "_saved_api_key", ""))

        if self._api_key_save_btn is not None:
            self._api_key_save_btn.setEnabled(bool(key_text))
        if self._api_key_test_btn is not None:
            self._api_key_test_btn.setEnabled(bool(key_text) and self._api_test_worker is None)
        if self._api_key_remove_btn is not None:
            self._api_key_remove_btn.setEnabled(bool(key_text) or saved)

    def _on_toggle_api_key_reveal(self, checked: bool):
        """Handle toggle api key reveal callbacks."""
        if self._api_key_input is None or self._api_key_reveal_btn is None:
            return
        self._api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._api_key_reveal_btn.setText("Hide" if checked else "Reveal")

    def _on_save_api_key_clicked(self):
        """Handle save api key clicked callbacks."""
        if self._api_key_input is None:
            return
        key = self._api_key_input.text().strip()
        if not key:
            self.toast.show_message("Enter an API key to save.", kind="warn")
            return
        if not hasattr(self, "_client") or self._client is None:
            self.toast.show_message("Client unavailable for save.", kind="error")
            return
        result = self._client.save_api_key(key)
        if "error" in result:
            self.toast.show_message(str(result["error"]), kind="error")
            return
        self._saved_api_key = key
        self._update_api_key_action_state()
        self.toast.show_message("API key saved locally via backend.", kind="success")

    def _on_remove_api_key_clicked(self):
        """Handle remove api key clicked callbacks."""
        if self._api_key_input is not None:
            self._api_key_input.clear()
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self._api_key_reveal_btn is not None:
            blocker = QSignalBlocker(self._api_key_reveal_btn)
            self._api_key_reveal_btn.setChecked(False)
            self._api_key_reveal_btn.setText("Reveal")
            del blocker
        if not hasattr(self, "_client") or self._client is None:
            self.toast.show_message("Client unavailable for remove.", kind="error")
            return
        result = self._client.remove_api_key()
        if "error" in result:
            self.toast.show_message(str(result["error"]), kind="error")
            return
        self._saved_api_key = ""
        self._update_api_key_action_state()
        self.toast.show_message("Stored API key removed.", kind="warn")

    def _on_test_api_key_clicked(self):
        """Handle test api key clicked callbacks."""
        if self._api_key_input is None or self._api_test_worker is not None:
            return

        key = self._api_key_input.text().strip()
        if not key:
            self.toast.show_message("Enter an API key first.", kind="warn")
            return

        self._api_test_worker = _ApiKeyTestWorker(self._client, key)
        self._api_test_worker.result_ready.connect(self._on_api_key_test_result)
        self._api_test_worker.finished.connect(self._on_api_key_test_finished)

        if self._api_key_test_btn is not None:
            self._api_key_test_btn.setEnabled(False)
            self._api_key_test_btn.setText("Testing...")
        self._api_test_worker.start()

    def _on_api_key_test_result(self, ok: bool, message: str):
        """Handle api key test result callbacks."""
        self.toast.show_message(message, kind="success" if ok else "error")

    def _on_api_key_test_finished(self):
        """Handle api key test finished callbacks."""
        if self._api_key_test_btn is not None:
            self._api_key_test_btn.setText("Test Connection")
        self._api_test_worker = None
        self._update_api_key_action_state()

    def _update_settings_theme(self, tokens: dict):
        """Update settings theme."""
        t = tokens
        panel_radius = max(0, CardWidget.RADIUS - 1)
        accent = t["accent.primary"]
        accent_hover = t["accent.hover"]
        accent_pressed = t["accent.pressed"]
        focus_ring = t["focusRing"]
        input_bg = t.get("settings.bg.input", t["bg.elevated"])
        page_bg = t.get("settings.bg.window", t["bg.surface"])
        sidebar_bg = t.get("settings.bg.sidebar", t["bg.elevated"])
        content_bg = t.get("settings.bg.content", t["bg.surface"])
        card_bg = t.get("settings.bg.card", t["bg.elevated"])
        divider = t.get("settings.divider", t["border.subtle"])
        border_subtle = t.get("settings.border.subtle", t["border.subtle"])
        border_strong = t.get("settings.border.strong", t["border.strong"])

        page_css = f"""
            QWidget#settingsPage {{
                background: {page_bg};
                border: none;
                border-bottom-left-radius: {panel_radius}px;
                border-bottom-right-radius: {panel_radius}px;
            }}
            QWidget#settingsSidebar {{
                background: {sidebar_bg};
                border: none;
                border-bottom-left-radius: {panel_radius}px;
            }}
            QWidget#settingsSidebarDivider {{
                background: {divider};
                border: none;
            }}
            QWidget#settingsContent {{
                background: {content_bg};
                border: none;
                border-bottom-right-radius: {panel_radius}px;
            }}
            QStackedWidget#settingsStack {{
                background: transparent;
                border: none;
                border-bottom-right-radius: {panel_radius}px;
            }}
            QScrollArea#settingsScroll {{
                background: transparent;
                border: none;
                border-bottom-right-radius: {panel_radius}px;
            }}
            QAbstractScrollArea#settingsScroll > QWidget > QWidget {{
                background: transparent;
            }}
            QWidget#settingsContentInner {{
                background: transparent;
                border: none;
            }}
            QLabel#settingsHeading {{
                font-family: {FONT_STACK};
                font-size: 20px;
                font-weight: 700;
                color: {t['text.primary']};
                letter-spacing: 0.2px;
                background: transparent;
                border: none;
            }}
            QLabel#settingsHeadingSub {{
                font-family: {FONT_STACK};
                font-size: 12px;
                font-weight: 400;
                color: {t['text.secondary']};
                background: transparent;
                border: none;
                margin-bottom: 2px;
            }}
            QWidget#settingsCard {{
                background: {card_bg};
                border: 1px solid {border_subtle};
                border-radius: {SETTINGS_METRICS['card_radius']}px;
            }}
            QWidget#settingsCardRowDivider {{
                background: {divider};
                border: none;
            }}
            QWidget#settingsRow {{
                background: transparent;
                border: none;
            }}
            QLabel#settingsRowLabel {{
                font-family: {FONT_STACK};
                font-size: 14px;
                font-weight: 600;
                color: {t['text.primary']};
                background: transparent;
                border: none;
            }}
            QLabel#settingsRowSub {{
                font-family: {FONT_STACK};
                font-size: 11px;
                font-weight: 400;
                color: {t['text.secondary']};
                background: transparent;
                border: none;
            }}
            QLabel#settingsHint {{
                font-family: {FONT_STACK};
                font-size: 11px;
                font-weight: 400;
                color: {t['text.muted']};
                background: transparent;
                border: none;
            }}
            QLineEdit#settingsInput {{
                font-family: {FONT_STACK};
                font-size: 13px;
                color: {t['text.primary']};
                background: {input_bg};
                border: 1px solid {border_strong};
                border-radius: 9px;
                padding: 0 10px;
                selection-background-color: {t['selection']};
            }}
            QLineEdit#settingsInput:hover {{
                border: 1px solid {t['text.secondary']};
            }}
            QLineEdit#settingsInput:focus {{
                border: 1px solid {accent};
                selection-background-color: {focus_ring};
            }}
            QLineEdit#settingsInput::placeholder {{
                color: {t['text.muted']};
            }}
            /* Combo box styled directly via _ModeComboBox.apply_theme() */
            QPushButton#settingsActionButton {{
                font-family: {FONT_STACK};
                font-size: 12px;
                font-weight: 600;
                border-radius: 8px;
                padding: 0 12px;
                min-height: {SETTINGS_METRICS['action_btn_h']}px;
                max-height: {SETTINGS_METRICS['action_btn_h']}px;
                min-width: 60px;
            }}
            QPushButton#settingsActionButton[role=\"primary\"] {{
                color: #ffffff;
                background: {accent};
                border: 1px solid {accent};
            }}
            QPushButton#settingsActionButton[role=\"primary\"]:hover {{
                background: {accent_hover};
                border: 1px solid {accent_hover};
            }}
            QPushButton#settingsActionButton[role=\"primary\"]:pressed {{
                background: {accent_pressed};
                border: 1px solid {accent_pressed};
            }}
            QPushButton#settingsActionButton[role=\"secondary\"] {{
                color: {t['text.primary']};
                background: {input_bg};
                border: 1px solid {border_strong};
            }}
            QPushButton#settingsActionButton[role=\"secondary\"]:hover {{
                border: 1px solid {accent};
                color: {accent};
            }}
            QPushButton#settingsActionButton[role=\"danger\"] {{
                color: {t['state.error']};
                background: {input_bg};
                border: 1px solid {t['state.error']};
            }}
            QPushButton#settingsActionButton[role=\"danger\"]:hover {{
                background: {t['state.errorBg']};
            }}
            QPushButton#settingsActionButton[role=\"ghost\"] {{
                color: {t['text.secondary']};
                background: transparent;
                border: 1px solid {border_strong};
            }}
            QPushButton#settingsActionButton[role=\"ghost\"]:hover {{
                color: {accent};
                border: 1px solid {accent};
            }}
            QPushButton#settingsActionButton:disabled {{
                color: {t['text.muted']};
                background: {input_bg};
                border: 1px solid {border_subtle};
            }}
        """
        if hasattr(self, "_settings_container"):
            self._settings_container.setStyleSheet(page_css)
        for combo in getattr(self, "_settings_selects", []):
            if hasattr(combo, "apply_theme"):
                combo.apply_theme(tokens)

    def _switch_settings_tab(self, icon_key: str):
        """Handle switch settings tab."""
        tab_order = ["features", "appearance", "apikey", "security"]
        idx = tab_order.index(icon_key) if icon_key in tab_order else 0
        self._settings_stack.setCurrentIndex(idx)
        for key, btn in self._settings_tab_btns:
            btn.set_active(key == icon_key)


    def _show_settings(self):
        """Show settings."""
        if hasattr(self, '_theme_mode_combo'):
            idx = self._theme_mode_combo.findData(ThemeManager.preference())
            if idx >= 0:
                with QSignalBlocker(self._theme_mode_combo):
                    self._theme_mode_combo.setCurrentIndex(idx)
        self._update_api_key_action_state()
        self._chat_container.hide()
        self._settings_container.show()
        self.composer.hide()
        self.header.enter_settings_mode()

    def _show_chat(self):
        """Show chat."""
        self._settings_container.hide()
        self._chat_container.show()
        self.composer.show()
        self.header.exit_settings_mode()
        self._update_toast_anchor()

    def _on_settings_color_mode_changed(self, _index: int):
        """Handle settings color mode changed callbacks."""
        mode = self._theme_mode_combo.currentData()
        if mode in ("dark", "light", "system"):
            ThemeManager.set_theme(mode)
