"""
sts_panel.py  –  Speech-to-Speech UI panel (frontend only, no logic).

Signals the host window what to do; all actual STT/TTS wiring lives in window.py.

Layout
──────
  ┌──────────────────────────────┐
  │  ← Back          Voice Chat  │  topbar
  ├──────────────────────────────┤
  │                              │
  │        ● waveform orb        │  main area
  │                              │
  │     ──── transcript ────     │
  │                              │
  ├──────────────────────────────┤
  │      [■ Stop / ● Start]      │  bottom bar
  └──────────────────────────────┘
"""

import math
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, QPointF, QSize, pyqtSignal,
    QPropertyAnimation, QEasingCurve, pyqtProperty,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath,
    QRadialGradient, QFont,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QAbstractButton, QSizePolicy, QScrollArea, QFrame,
)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))
from theme import ThemeManager, FONT_FAMILY_UI, FONT_STACK


# ── State constants ────────────────────────────────────────────────────────────
STATE_IDLE       = "idle"
STATE_LISTENING  = "listening"
STATE_THINKING   = "thinking"
STATE_SPEAKING   = "speaking"

# ── Back button ────────────────────────────────────────────────────────────────

class _BackButton(QAbstractButton):
    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._hovered = False
        self._size = QSize(76, 30)
        self.setFixedSize(self._size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Back")
        self._update_size()

    def apply_theme(self, t):
        self._tokens = t
        self.update()

    def _font(self):
        f = QFont(FONT_FAMILY_UI)
        f.setPointSizeF(10.5)
        f.setWeight(QFont.Weight.Medium)
        return f

    def _update_size(self):
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font())
        h = max(30, fm.height() + 8)
        w = max(70, fm.horizontalAdvance("Back") + 34)
        self._size = QSize(w, h)
        self.setFixedSize(self._size)

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def sizeHint(self):
        return QSize(self._size)

    def minimumSizeHint(self):
        return QSize(self._size)

    def paintEvent(self, _):
        t = self._tokens
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        radius = 8.0

        bg = QColor(t["bg.elevated"])
        border = QColor(t["border.subtle"])
        icon = QColor(t["text.secondary"])
        border_w = 0.8

        if self._hovered:
            bg = QColor(t["accent.primary"])
            bg.setAlphaF(0.12)
            border = QColor(t["accent.primary"])
            border.setAlphaF(0.26)
            icon = QColor(t["accent.primary"])
        elif self.isDown():
            bg = QColor(t["accent.primary"])
            bg.setAlphaF(0.16)
            border = QColor(t["accent.primary"])
            border.setAlphaF(0.30)
            icon = QColor(t["accent.primary"])
        else:
            bg.setAlphaF(0.22)
            border.setAlphaF(0.10)

        p.setBrush(QBrush(bg))
        p.setPen(QPen(border, border_w))
        p.drawRoundedRect(rect, radius, radius)

        if self.hasFocus():
            focus = QColor(t["focusRing"])
            focus.setAlphaF(0.55)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(focus, 1.0))
            p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), radius - 2, radius - 2)

        pen = QPen(icon, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        arm = 4.6
        cx = 12.0
        cy = h / 2.0
        p.drawLine(QPointF(cx + arm * 0.72, cy - arm), QPointF(cx, cy))
        p.drawLine(QPointF(cx, cy), QPointF(cx + arm * 0.72, cy + arm))

        p.setPen(icon)
        p.setFont(self._font())
        p.drawText(
            QRectF(21.0, 0, w - 24.0, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "Back",
        )
        p.end()


# ── Animated waveform orb ──────────────────────────────────────────────────────

class _WaveformOrb(QWidget):
    """
    Large central orb with animated concentric rings and bar waveform.
    Driven purely by QPropertyAnimation on `_phase`.
    """
    ORB_R   = 72
    RING_N  = 3
    BAR_N   = 20

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._state  = STATE_IDLE
        self._phase  = 0.0
        self.setFixedSize(260, 260)

        self._anim = QPropertyAnimation(self, b"phase", self)
        self._anim.setDuration(2200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)

    def _get_phase(self): return self._phase
    def _set_phase(self, v): self._phase = v; self.update()
    phase = pyqtProperty(float, _get_phase, _set_phase)

    def set_state(self, state: str):
        self._state = state
        if state == STATE_IDLE:
            self._anim.stop()
            self._phase = 0.0
        else:
            if not self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.start()
        self.update()

    def apply_theme(self, t): self._tokens = t; self.update()

    def paintEvent(self, _):
        t  = self._tokens
        p  = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width()  / 2.0
        cy = self.height() / 2.0
        r  = float(self.ORB_R)

        accent = QColor(t["accent.primary"])
        active = self._state != STATE_IDLE

        # ── Outer animated rings ──────────────────────
        if active:
            for i in range(self.RING_N):
                ring_phase = (self._phase + i / self.RING_N) % 1.0
                ring_r  = r + 18 + ring_phase * 38
                alpha   = max(0.0, 0.22 * (1.0 - ring_phase))
                rc = QColor(accent); rc.setAlphaF(alpha)
                pen = QPen(rc, 1.2)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # ── Orb background ────────────────────────────
        grad = QRadialGradient(cx, cy, r)
        if active:
            inner = QColor(accent); inner.setAlphaF(0.22)
            outer = QColor(accent); outer.setAlphaF(0.05)
        else:
            inner = QColor(t["bg.elevated"])
            outer = QColor(t["bg.canvas"])
        grad.setColorAt(0.0, inner)
        grad.setColorAt(1.0, outer)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # ── Orb border ring ───────────────────────────
        border_c = QColor(accent if active else t["border.strong"])
        border_c.setAlphaF(0.55 if active else 0.25)
        p.setPen(QPen(border_c, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # ── Waveform bars ─────────────────────────────
        bar_pen_c = QColor(accent if active else QColor(t["text.muted"]))
        bar_pen_c.setAlphaF(0.90 if active else 0.35)
        pen = QPen(bar_pen_c, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        for i in range(self.BAR_N):
            angle_rad = 2 * math.pi * i / self.BAR_N
            if active:
                wave  = math.sin(self._phase * 2 * math.pi + i * 0.6) * 0.5 + 0.5
                bar_h = 8.0 + wave * 22.0
            else:
                # Static short bars when idle
                bar_h = 6.0 + 4.0 * abs(math.sin(i * 0.7))

            inner_r = r - bar_h
            outer_r = r - 4.0
            p1 = QPointF(cx + inner_r * math.cos(angle_rad),
                         cy + inner_r * math.sin(angle_rad))
            p2 = QPointF(cx + outer_r * math.cos(angle_rad),
                         cy + outer_r * math.sin(angle_rad))
            p.drawLine(p1, p2)

        # ── Center mic icon ───────────────────────────
        ic = QColor(accent if active else QColor(t["text.secondary"]))
        ic.setAlphaF(0.9)
        mic_pen = QPen(ic, 2.0)
        mic_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        mic_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(mic_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Mic body
        body = QPainterPath()
        body.addRoundedRect(QRectF(cx - 8, cy - 16, 16, 22), 8, 8)
        p.drawPath(body)
        # Mic arc
        p.drawArc(QRectF(cx - 14, cy + 2, 28, 16), 0, -180 * 16)
        # Stand
        p.drawLine(QPointF(cx, cy + 18), QPointF(cx, cy + 24))
        p.drawLine(QPointF(cx - 8, cy + 24), QPointF(cx + 8, cy + 24))

        p.end()


# ── Transcript display ─────────────────────────────────────────────────────────

class _TranscriptBubble(QFrame):
    """Scrollable transcript area showing user/assistant lines."""

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self.setObjectName("transcriptFrame")
        self.setMinimumHeight(60)
        self.setMaximumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("transcriptScroll")
        lay.addWidget(scroll)

        self._inner = QWidget()
        self._inner.setObjectName("transcriptInner")
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(16, 10, 16, 10)
        self._inner_lay.setSpacing(6)
        self._inner_lay.addStretch()
        scroll.setWidget(self._inner)
        self._scroll = scroll

        self._apply_style()

    def add_line(self, text: str, role: str = "user"):
        """Add a transcript line. role = 'user' | 'assistant'."""
        t    = self._tokens
        lbl  = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        color = t["text.primary"] if role == "assistant" else t["text.secondary"]
        weight = "600" if role == "user" else "400"
        lbl.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
            f" font-family: {FONT_STACK}; font-size: 13px; font-weight: {weight};"
        )
        # Insert before the stretch
        self._inner_lay.insertWidget(self._inner_lay.count() - 1, lbl)
        # Scroll to bottom
        QTimer.singleShot(30, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def clear_transcript(self):
        while self._inner_lay.count() > 1:
            item = self._inner_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def apply_theme(self, t):
        self._tokens = t
        self._apply_style()

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QFrame#transcriptFrame {{
                background: transparent;
                border: none;
            }}
            QScrollArea#transcriptScroll {{
                background: transparent;
                border: none;
            }}
            QWidget#transcriptInner {{
                background: transparent;
            }}
        """)


# ── Start / Stop action button ─────────────────────────────────────────────────

class _ActionButton(QAbstractButton):
    SIZE_W = 160
    SIZE_H = 52

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens  = tokens
        self._state   = STATE_IDLE
        self._hovered = False
        self.setFixedSize(self.SIZE_W, self.SIZE_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_state(self, state: str):
        self._state = state
        self.update()

    def apply_theme(self, t): self._tokens = t; self.update()

    def enterEvent(self, e): self._hovered = True;  self.update()
    def leaveEvent(self, e): self._hovered = False; self.update()

    def _label(self):
        return "Stop" if self._state != STATE_IDLE else "Start"

    def paintEvent(self, _):
        t   = self._tokens
        p   = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.SIZE_W), float(self.SIZE_H)
        r    = h / 2

        active = self._state != STATE_IDLE

        if active:
            bg = QColor(t["state.error"] if self._hovered else "#C84040")
        else:
            bg = QColor(t["accent.hover"] if self._hovered else t["accent.primary"])

        if self.isDown():
            bg = bg.darker(115)

        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Icon
        ic_color = QColor("#FFFFFF")
        cx, cy = w / 2 - 18, h / 2

        if active:
            # Stop square
            sq = 8.0
            p.setBrush(QBrush(ic_color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(cx - sq / 2, cy - sq / 2, sq, sq), 2, 2)
        else:
            # Play triangle
            p.setBrush(QBrush(ic_color))
            p.setPen(Qt.PenStyle.NoPen)
            tri = QPainterPath()
            tri.moveTo(cx - 5, cy - 7)
            tri.lineTo(cx - 5, cy + 7)
            tri.lineTo(cx + 7, cy)
            tri.closeSubpath()
            p.drawPath(tri)

        # Label
        p.setPen(ic_color)
        f = QFont(FONT_FAMILY_UI)
        f.setPointSizeF(13)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.drawText(QRectF(cx + 12, 0, w - cx - 16, h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._label())
        p.end()


# ── Main panel ─────────────────────────────────────────────────────────────────

class SpeechToSpeechPanel(QWidget):
    """
    Full speech-to-speech UI panel.  Frontend only — no STT/TTS logic.

    Signals emitted (host window wires these to actual logic):
        back_requested()        – user pressed Back
        start_requested()       – user pressed Start
        stop_requested()        – user pressed Stop
    """

    back_requested  = pyqtSignal()
    start_requested = pyqtSignal()
    stop_requested  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens = ThemeManager.tokens()
        self._state  = STATE_IDLE
        self._build_ui()
        ThemeManager.subscribe(self._on_theme)

    # ── Public API ──────────────────────────────

    def set_state(self, state: str):
        """Called by host window to update visual state."""
        assert state in (STATE_IDLE, STATE_LISTENING, STATE_THINKING, STATE_SPEAKING)
        self._state = state
        self._orb.set_state(state)
        self._action_btn.set_state(state)

    def add_transcript_line(self, text: str, role: str = "user"):
        """Append a line to the transcript. role='user'|'assistant'"""
        self._transcript.add_line(text, role)

    def clear_transcript(self):
        self._transcript.clear_transcript()

    # ── Build UI ────────────────────────────────

    def _build_ui(self):
        t    = self._tokens
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(52)
        topbar.setObjectName("stsTopBar")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(14, 8, 16, 8)
        tb.setSpacing(12)

        self._back_btn = _BackButton(t)
        self._back_btn.clicked.connect(self.back_requested)
        tb.addWidget(self._back_btn)

        title_lbl = QLabel("Voice Chat")
        title_lbl.setObjectName("stsTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        tb.addWidget(title_lbl)

        tb.addStretch()

        root.addWidget(topbar)

        # ── Divider ──────────────────────────────
        div = QFrame(); div.setFixedHeight(1); div.setObjectName("stsDivider")
        root.addWidget(div)

        # ── Main area ────────────────────────────
        main = QWidget()
        main.setObjectName("stsMain")
        main_lay = QVBoxLayout(main)
        main_lay.setContentsMargins(32, 28, 32, 20)
        main_lay.setSpacing(0)
        main_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._orb = _WaveformOrb(t)
        main_lay.addWidget(self._orb, 0, Qt.AlignmentFlag.AlignHCenter)

        main_lay.addSpacing(24)

        # Transcript
        self._transcript = _TranscriptBubble(t)
        main_lay.addWidget(self._transcript, 1)

        root.addWidget(main, 1)

        # ── Bottom bar ───────────────────────────
        bottom = QWidget()
        bottom.setObjectName("stsBottom")
        btm_lay = QHBoxLayout(bottom)
        btm_lay.setContentsMargins(32, 14, 32, 20)
        btm_lay.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._action_btn = _ActionButton(t)
        self._action_btn.clicked.connect(self._on_action)
        btm_lay.addWidget(self._action_btn)

        root.addWidget(bottom)

        self._apply_style()

    def _on_action(self):
        if self._state == STATE_IDLE:
            self.start_requested.emit()
        else:
            self.stop_requested.emit()

    # ── Theme ────────────────────────────────────

    def _on_theme(self, tokens):
        self._tokens = tokens
        self._apply_style()
        for w in (self._back_btn, self._orb,
                  self._transcript, self._action_btn):
            w.apply_theme(tokens)

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QWidget#stsTopBar {{
                background: {t['bg.surface']};
            }}
            QLabel#stsTitle {{
                font-family: {FONT_STACK};
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.3px;
                color: {t['text.primary']};
                background: transparent;
            }}
            QFrame#stsDivider {{
                background: {t['border.subtle']};
                border: none;
            }}
            QWidget#stsMain {{
                background: {t['bg.canvas']};
            }}
            QWidget#stsBottom {{
                background: {t['bg.surface']};
                border-top: 1px solid {t['border.subtle']};
            }}
        """)

    def __del__(self):
        try:
            ThemeManager.unsubscribe(self._on_theme)
        except Exception:
            pass
