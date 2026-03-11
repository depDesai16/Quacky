from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QFrame,
)

from theme import FONT_STACK


class TimersEventsPanel(QWidget):
    closed = pyqtSignal()

    RADIUS = 14

    def __init__(self, tokens: dict, fetch_dashboard: Callable[[], dict], parent=None):
        super().__init__(
            parent,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self._tokens = tokens
        self._fetch_dashboard = fetch_dashboard
        self.setWindowTitle("Quacky - Timers & Events")
        self.setObjectName("quacky-timers-events-panel")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(520, 430)
        self.setAutoFillBackground(False)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(15000)
        self._refresh_timer.timeout.connect(self.refresh_now)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel("Timers & Events")
        header.addWidget(self._title, 1)
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh_now)
        header.addWidget(self._refresh_btn, 0)
        outer.addLayout(header)

        self._sub = QLabel("Live timers/alarms and recently generated calendar actions.")
        outer.addWidget(self._sub)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("timersEventsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.viewport().setObjectName("timersEventsViewport")

        self._content = QWidget()
        self._content.setObjectName("timersEventsContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(14)

        self._timers_title = QLabel("ACTIVE TIMERS / ALARMS")
        self._timers_body = QLabel("")
        self._timers_body.setWordWrap(True)

        self._events_title = QLabel("RECENT CALENDAR EVENTS")
        self._events_body = QLabel("")
        self._events_body.setWordWrap(True)

        self._content_layout.addWidget(self._timers_title)
        self._content_layout.addWidget(self._timers_body)
        self._content_layout.addWidget(self._events_title)
        self._content_layout.addWidget(self._events_body)
        self._content_layout.addStretch(1)
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, 1)

        self.apply_theme(tokens)

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        t = self._tokens
        self._title.setStyleSheet(
            f"font-family: {FONT_STACK}; font-size: 16px; font-weight: 700;"
            f"color: {t['text.primary']}; background: transparent;"
        )
        self._sub.setStyleSheet(
            f"font-family: {FONT_STACK}; font-size: 12px; font-weight: 400;"
            f"color: {t['text.secondary']}; background: transparent;"
        )
        section_style = (
            f"font-family: {FONT_STACK}; font-size: 10px; font-weight: 700;"
            f"letter-spacing: 0.8px; color: {t['text.muted']}; background: transparent;"
        )
        self._timers_title.setStyleSheet(section_style)
        self._events_title.setStyleSheet(section_style)
        body_style = (
            f"font-family: {FONT_STACK}; font-size: 13px; font-weight: 400;"
            f"color: {t['text.primary']}; background: transparent;"
        )
        self._timers_body.setStyleSheet(body_style)
        self._events_body.setStyleSheet(body_style)

        self.setStyleSheet(
            f"""
            QWidget#quacky-timers-events-panel {{
                background: transparent;
            }}
            QScrollArea#timersEventsScroll {{
                background: transparent;
                border: none;
            }}
            QWidget#timersEventsViewport,
            QWidget#timersEventsContent {{
                background: transparent;
                border: none;
            }}
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
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: {t['scrollbar.track']};
                border: none;
                border-radius: 5px;
                margin: 0px 1px 0px 1px;
            }}
            """
        )

        self._refresh_btn.setStyleSheet(
            "QPushButton {"
            f"font-family: {FONT_STACK}; font-size: 12px; font-weight: 600;"
            f"color: {t['text.primary']}; background: {t['bg.surface']};"
            f"border: 1px solid {t['border.strong']}; border-radius: 8px; padding: 6px 10px;"
            "}"
            "QPushButton:hover {"
            f"background: {t['accent.subtleBg']};"
            f"border-color: {t['accent.primary']};"
            "}"
            "QPushButton:pressed {"
            f"background: {t['accent.subtleBg']};"
            f"border-color: {t['accent.pressed']};"
            "}"
        )
        self.update()

    def _format_timers(self, timers: list[dict]) -> str:
        if not timers:
            return "No active timers or alarms."
        lines = []
        for timer in timers[:20]:
            kind = str(timer.get("kind", "timer")).strip().capitalize()
            timer_id = str(timer.get("timer_id", "")).strip()
            label = str(timer.get("label", "")).strip()
            remaining = str(timer.get("remaining_text", "")).strip()
            due = str(timer.get("due_at", "")).strip()
            label_suffix = f" ({label})" if label else ""
            due_text = f" | due {due}" if due else ""
            remaining_text = f" | {remaining} left" if remaining else ""
            lines.append(f"- {kind} {timer_id}{label_suffix}{remaining_text}{due_text}")
        return "\n".join(lines)

    def _format_events(self, events: list[dict]) -> str:
        if not events:
            return "No recent calendar actions recorded yet."
        lines = []
        for event in events[:30]:
            action = str(event.get("action", "event")).strip().capitalize()
            title = str(event.get("title", "(untitled)")).strip() or "(untitled)"
            created_at = str(event.get("created_at", "")).strip()
            start = str(event.get("start_time", "")).strip()
            end = str(event.get("end_time", "")).strip()
            status = str(event.get("status", "ok")).strip().lower()
            status_chip = "ok" if status == "ok" else "issue"
            span = ""
            if start and end:
                span = f" | {start} -> {end}"
            elif start:
                span = f" | {start}"
            when = f" [{created_at}]" if created_at else ""
            lines.append(f"- {action}: {title}{span}{when} ({status_chip})")
        return "\n".join(lines)

    def refresh_now(self):
        try:
            payload = self._fetch_dashboard() or {}
        except Exception as exc:
            self._timers_body.setText("Failed to load timers.")
            self._events_body.setText(f"Failed to load events: {exc}")
            return

        timers = payload.get("timers") if isinstance(payload, dict) else []
        events = payload.get("events") if isinstance(payload, dict) else []
        if not isinstance(timers, list):
            timers = []
        if not isinstance(events, list):
            events = []
        self._timers_body.setText(self._format_timers(timers))
        self._events_body.setText(self._format_events(events))

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_now()
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()

    def closeEvent(self, event):
        self._refresh_timer.stop()
        self.closed.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Escape,):
            self.close()
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event):
        t = self._tokens
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)
        painter.fillPath(path, QColor(t["bg.elevated"]))
        border = QPen(QColor(t["border.subtle"]), 1)
        border.setCosmetic(True)
        painter.setPen(border)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.end()
