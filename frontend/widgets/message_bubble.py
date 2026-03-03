"""
widgets/message_bubble.py
"""

import html
import re

from PyQt6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout,
                              QSizePolicy, QGraphicsOpacityEffect)

from theme import ThemeManager, FONT_STACK, FONT_MONO

_DEFAULT_MAX_W = 400
_APPEAR_MS = 180



def animate_in_widget(widget: QWidget, duration_ms: int = _APPEAR_MS):
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    widget._appear_effect = effect
    widget._appear_anim   = anim



def _code_span_style(t: dict) -> str:
    return (f"background-color:{t['bg.elevated']};"
            f"font-family:{FONT_MONO};font-size:12px;"
            f"border-radius:3px;padding:1px 4px;")


def _pre_style(t: dict) -> str:
    return (f"background-color:#0d0d1c;border-radius:6px;"
            f"padding:10px 12px;font-family:{FONT_MONO};font-size:12px;"
            f"white-space:pre-wrap;color:{t['text.primary']};margin:6px 0;")


def _is_structured_md_line(line: str) -> bool:
    s = line.lstrip()
    return bool(
        re.match(
            r"^(#{1,6}\s|[*+-]\s|\d+\.\s|>\s|```|~~~|\|.+\||-{3,}$|_{3,}$|\*{3,}$)",
            s,
        )
    )


def _normalize_assistant_text(text: str) -> str:
    """
    Make plain prose wrap naturally by collapsing single hard line breaks,
    while preserving markdown structures and fenced code blocks.
    """
    if not text or "\n" not in text:
        return text

    lines = text.splitlines()
    out: list[str] = []
    paragraph_buf: list[str] = []
    in_code = False

    def flush_paragraph():
        if paragraph_buf:
            out.append(" ".join(part.strip() for part in paragraph_buf if part.strip()))
            paragraph_buf.clear()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_paragraph()
            out.append(line)
            in_code = not in_code
            continue

        if in_code:
            out.append(line)
            continue

        if stripped == "":
            flush_paragraph()
            out.append("")
            continue

        if _is_structured_md_line(line):
            flush_paragraph()
            out.append(line)
            continue

        paragraph_buf.append(line)

    flush_paragraph()

    compact: list[str] = []
    prev_blank = False
    for line in out:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        compact.append(line)
        prev_blank = is_blank

    return "\n".join(compact)


def _reading_metrics(text: str) -> tuple[float, float, int]:
    """
    Slightly tighten typography for long assistant responses so dense outputs
    remain readable without looking oversized.
    """
    n = len(text)
    if n >= 1100:
        return (13.8, 1.70, 5)
    if n >= 650:
        return (14.0, 1.68, 6)
    if n >= 320:
        return (14.25, 1.65, 6)
    return (14.5, 1.62, 7)


def render_markdown(text: str, tokens: dict) -> str:
    t = tokens
    text = _normalize_assistant_text(text)
    font_size, line_height, p_margin = _reading_metrics(text)
    try:
        import markdown as _md
        body = _md.markdown(text, extensions=["fenced_code", "tables", "nl2br"])
        cs   = _code_span_style(t)
        ps   = _pre_style(t)
        body = re.sub(r'<code>', f'<code style="{cs}">', body)
        body = re.sub(r'<pre>',  f'<pre style="{ps}">',  body)
    except ImportError:
        body = _mini_render(text, t)

    return (
        f'<html><head><style>'
        f'body{{font-family:{FONT_STACK};font-size:{font_size}px;'
        f'line-height:{line_height};color:{t["text.primary"]};margin:0;padding:0;}}'
        f'a{{color:{t["accent.primary"]};text-decoration:none;}}'
        f'b,strong{{font-weight:600;}}'
        f'ul,ol{{margin:4px 0 4px 18px;padding:0;}}'
        f'li{{margin-bottom:3px;}}'
        f'p{{margin:0 0 {p_margin}px;}}'
        f'h1{{font-size:17px;font-weight:600;margin:8px 0 4px;}}'
        f'h2{{font-size:15px;font-weight:600;margin:6px 0 4px;}}'
        f'h3{{font-size:14px;font-weight:600;margin:4px 0 2px;}}'
        f'blockquote{{border-left:3px solid {t["accent.primary"]};'
        f'margin:4px 0;padding-left:10px;color:{t["text.secondary"]};}}'
        f'</style></head><body>{body}</body></html>'
    )


def _mini_render(text: str, tokens: dict) -> str:
    t        = tokens
    cs       = _code_span_style(t)
    ps       = _pre_style(t)
    lines    = text.split("\n")
    out      = []
    in_code  = False
    code_buf = []

    for line in lines:
        if line.strip().startswith("```"):
            if in_code:
                out.append(
                    f'<pre style="{ps}">'
                    f'{html.escape(chr(10).join(code_buf))}</pre>'
                )
                code_buf = []
                in_code  = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue
        if line.startswith("### "):
            out.append(f'<h3>{html.escape(line[4:])}</h3>'); continue
        if line.startswith("## "):
            out.append(f'<h2>{html.escape(line[3:])}</h2>'); continue
        if line.startswith("# "):
            out.append(f'<h1>{html.escape(line[2:])}</h1>'); continue
        m = re.match(r'^(\s*)[*\-]\s+(.*)', line)
        if m:
            out.append(f'<p>&nbsp;&nbsp;&nbsp;• {_inline(m.group(2), cs)}</p>')
            continue
        m2 = re.match(r'^\s*\d+\.\s+(.*)', line)
        if m2:
            out.append(f'<p>&nbsp;&nbsp;&nbsp;{_inline(m2.group(1), cs)}</p>')
            continue
        if line.startswith("> "):
            out.append(f'<blockquote>{_inline(line[2:], cs)}</blockquote>')
            continue
        if line.strip() == "":
            out.append("<br>")
            continue
        out.append(
            f'<p style="margin:0 0 2px;">{_inline(html.escape(line), cs)}</p>'
        )

    if in_code and code_buf:
        out.append(
            f'<pre style="{ps}">{html.escape(chr(10).join(code_buf))}</pre>'
        )
    return "".join(out)


def _inline(text: str, cs: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__',     r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_',       r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`',
                  lambda m: f'<code style="{cs}">{m.group(1)}</code>', text)
    text = re.sub(
        r'\[(.+?)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', text
    )
    return text



def _make_label(max_w: int = _DEFAULT_MAX_W) -> QLabel:
    lbl = QLabel()
    lbl.setWordWrap(True)
    lbl.setMaximumWidth(max_w)
    lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse |
        Qt.TextInteractionFlag.LinksAccessibleByMouse
    )
    lbl.setOpenExternalLinks(True)
    return lbl



class _BubbleBase(QFrame):
    """
    set_max_width(px) — called by ChatTimeline on every resize.
    The bubble never exceeds this width; it shrinks to content below it.
    """

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._max_w  = _DEFAULT_MAX_W

        self._label = _make_label(self._max_w)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(0)
        lay.addWidget(self._label)

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setFrameShape(QFrame.Shape.NoFrame)

    def set_max_width(self, w: int):
        if w == self._max_w:
            return
        self._max_w = w
        self._label.setMaximumWidth(w)
        self._label.updateGeometry()
        self.updateGeometry()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_frame_style()

    def _apply_frame_style(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QFrame {{
                background: {t[self._bg_token()]};
                border: 1px solid {t[self._border_token()]};
                {self._radius_css()}
            }}
            QLabel {{
                background: transparent; border: none;
                font-family: {FONT_STACK}; font-size: 14px;
                color: {t['text.primary']};
            }}
        """)

    def _bg_token(self) -> str:     raise NotImplementedError
    def _border_token(self) -> str: raise NotImplementedError
    def _radius_css(self) -> str:   raise NotImplementedError



class UserBubble(_BubbleBase):
    def __init__(self, text: str, tokens: dict, parent=None):
        super().__init__(tokens, parent)
        self._raw_text = text
        self._label.setText(html.escape(text).replace("\n", "<br>"))
        self._apply_frame_style()

    def _bg_token(self)     -> str: return "user.bg"
    def _border_token(self) -> str: return "user.border"
    def _radius_css(self)   -> str:
        return ("border-top-left-radius:14px; border-top-right-radius:4px;"
                "border-bottom-left-radius:14px; border-bottom-right-radius:14px;")



class AssistantBubble(QFrame):
    """
    Assistant response surface with mirrored chat-bubble corners.
    """

    def __init__(self, text: str, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens   = tokens
        self._raw_text = text
        self._max_w    = _DEFAULT_MAX_W

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._label = _make_label(self._max_w)
        self._label.setText(render_markdown(text, tokens))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 9, 14, 9)
        lay.setSpacing(0)
        lay.addWidget(self._label)

        self._apply_style()

    def set_max_width(self, w: int):
        if w == self._max_w:
            return
        self._max_w = w
        self._label.setMaximumWidth(w)
        self._label.updateGeometry()
        self.updateGeometry()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._label.setText(render_markdown(self._raw_text, tokens))
        self._apply_style()

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(
            "QFrame {"
            " background: transparent;"
            " border: none;"
            "}"
        )
        self._label.setStyleSheet(
            "QLabel { background: transparent; border: none;"
            " font-family: " + FONT_STACK + "; font-size: 14.5px;"
            " line-height: 1.68; color: " + t["text.primary"] + "; }"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt6.QtGui import QPainter, QColor, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._tokens["accent.primary"])
        c.setAlphaF(0.7)
        pen = QPen(c, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        x = 9
        p.drawLine(x, 10, x, max(10, self.height() - 10))
        p.end()



class StreamingAssistantBubble(QFrame):
    """
    In-place updating bubble. Chunks queued; flushed at most every UPDATE_MS.
    set_max_width() honoured immediately and on every flush.
    """

    UPDATE_MS = 60

    def __init__(self, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._raw   = ""
        self._queue = []
        self._max_w = _DEFAULT_MAX_W

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._label = _make_label(self._max_w)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 9, 14, 9)
        lay.setSpacing(0)
        lay.addWidget(self._label)

        self._apply_style()

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(self.UPDATE_MS)
        self._flush_timer.timeout.connect(self._flush)


    def append_chunk(self, chunk: str):
        self._queue.append(chunk)
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def finalize(self):
        self._flush_timer.stop()
        if self._queue:
            self._raw += "".join(self._queue)
            self._queue.clear()
            self._render()

    def get_text(self) -> str:
        return self._raw

    def set_max_width(self, w: int):
        if w == self._max_w:
            return
        self._max_w = w
        self._label.setMaximumWidth(w)
        self._label.updateGeometry()
        self.updateGeometry()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_style()
        self._render()

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(
            "QFrame {"
            " background: transparent;"
            " border: none;"
            "}"
        )
        self._label.setStyleSheet(
            "QLabel { background: transparent; border: none;"
            " font-family: " + FONT_STACK + "; font-size: 14.5px;"
            " line-height: 1.68;"
            " color: " + t["text.primary"] + "; }"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        from PyQt6.QtGui import QPainter, QColor, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._tokens["accent.primary"])
        c.setAlphaF(0.7)
        pen = QPen(c, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        x = 9
        p.drawLine(x, 10, x, max(10, self.height() - 10))
        p.end()


    def _flush(self):
        if not self._queue:
            self._flush_timer.stop()
            return
        self._raw += "".join(self._queue)
        self._queue.clear()
        self._render()

    def _render(self):
        self._label.setText(render_markdown(self._raw, self._tokens))
        self._label.updateGeometry()
        self.updateGeometry()
        p = self.parent()
        while p is not None:
            p.updateGeometry()
            try:
                p = p.parent()
            except Exception:
                break



class SystemMessage(QLabel):
    def __init__(self, html_text: str, tokens: dict, parent=None):
        super().__init__(parent)
        self._tokens = tokens
        self._html_text = html_text
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setText(html_text)
        self._apply_style()

    def apply_theme(self, tokens: dict):
        self._tokens = tokens
        self._apply_style()

    def _apply_style(self):
        t = self._tokens
        self.setStyleSheet(f"""
            QLabel {{
                color: {t['text.muted']}; font-family: {FONT_STACK};
                font-size: 12px; background: transparent; border: none;
                padding: 2px 16px;
            }}
        """)
