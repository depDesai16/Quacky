
import sys

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QGuiApplication, QPalette


DARK_TOKENS: dict = {
    "bg.canvas":        "#141414",
    "bg.surface":       "#1C1C1C",
    "bg.elevated":      "#242424",
    "settings.bg.window":   "#181818",
    "settings.bg.sidebar":  "#1D1D1D",
    "settings.bg.content":  "#202020",
    "settings.bg.card":     "#262626",
    "settings.bg.input":    "#2D2D2D",

    "text.primary":     "#E8E8F0",
    "text.secondary":   "#9090A8",
    "text.muted":       "#55556A",

    "border.subtle":    "rgba(255,255,255,0.08)",
    "border.strong":    "rgba(255,255,255,0.16)",
    "settings.border.subtle": "rgba(255,255,255,0.09)",
    "settings.border.strong": "rgba(255,255,255,0.18)",
    "settings.divider":       "rgba(255,255,255,0.10)",
    "settings.shadow":        "rgba(0,0,0,0.34)",

    "accent.primary":   "#E8A020",
    "accent.hover":     "#F0B040",
    "accent.pressed":   "#C88010",
    "accent.subtleBg":  "rgba(232,160,32,0.12)",
    "newmsg.bg.top":          "#D88A1F",
    "newmsg.bg.bottom":       "#C97712",
    "newmsg.bg.top.hover":    "#E49A2F",
    "newmsg.bg.bottom.hover": "#D5841B",
    "newmsg.bg.top.pressed":  "#C87612",
    "newmsg.bg.bottom.pressed": "#B3670D",
    "newmsg.border":          "rgba(0,0,0,0.22)",
    "newmsg.border.hover":    "rgba(0,0,0,0.30)",
    "newmsg.fg":              "#FFFFFF",
    "newmsg.idle.fg":         "#D88A1F",
    "newmsg.idle.border":     "rgba(216,138,31,0.48)",

    "user.bg":          "rgba(232,160,32,0.15)",
    "user.border":      "rgba(232,160,32,0.30)",
    "asst.bg":          "#262A33",
    "asst.bg.top":      "#2D3240",
    "asst.bg.bottom":   "#242937",
    "asst.border":      "rgba(255,255,255,0.14)",
    "asst.line":        "rgba(232,160,32,0.88)",

    "state.success":    "#E8A020",
    "state.successBg":  "rgba(232,160,32,0.14)",
    "state.warn":       "#F0A030",
    "state.warnBg":     "rgba(240,160,48,0.12)",
    "state.error":      "#E05555",
    "state.errorBg":    "rgba(224,85,85,0.12)",

    "status.idle":      "#5A5A7A",
    "status.thinking":  "#7A8AFF",
    "status.responding":"#E8A020",
    "status.error":     "#E05555",

    "selection":        "rgba(232,160,32,0.30)",
    "focusRing":        "rgba(232,160,32,0.70)",

    "scrollbar.track":  "rgba(255,255,255,0.04)",
    "scrollbar.thumb":  "rgba(255,255,255,0.14)",
    "scrollbar.hover":  "rgba(255,255,255,0.24)",

    "shadow.color":     "#000000",
    "shadow.ambient_alpha": 140,          
    "shadow.key_alpha":      90,
}

LIGHT_TOKENS: dict = {
    "bg.canvas":        "#EEF0F5",
    "bg.surface":       "#FFFFFF",
    "bg.elevated":      "#F5F6FA",
    "settings.bg.window":   "#ECEFF4",
    "settings.bg.sidebar":  "#F3F5F9",
    "settings.bg.content":  "#F9FAFC",
    "settings.bg.card":     "#FFFFFF",
    "settings.bg.input":    "#F6F7FB",

    "text.primary":     "#18181E",
    "text.secondary":   "#606070",
    "text.muted":       "#A0A0B0",

    "border.subtle":    "rgba(0,0,0,0.07)",
    "border.strong":    "rgba(0,0,0,0.14)",
    "settings.border.subtle": "rgba(20,24,35,0.08)",
    "settings.border.strong": "rgba(20,24,35,0.16)",
    "settings.divider":       "rgba(20,24,35,0.10)",
    "settings.shadow":        "rgba(19,25,39,0.08)",

    "accent.primary":   "#C07010",
    "accent.hover":     "#D08020",
    "accent.pressed":   "#A06008",
    "accent.subtleBg":  "rgba(192,112,16,0.10)",
    "newmsg.bg.top":          "#D88A1F",
    "newmsg.bg.bottom":       "#C97712",
    "newmsg.bg.top.hover":    "#E49A2F",
    "newmsg.bg.bottom.hover": "#D5841B",
    "newmsg.bg.top.pressed":  "#C87612",
    "newmsg.bg.bottom.pressed": "#B3670D",
    "newmsg.border":          "rgba(0,0,0,0.22)",
    "newmsg.border.hover":    "rgba(0,0,0,0.30)",
    "newmsg.fg":              "#FFFFFF",
    "newmsg.idle.fg":         "#D88A1F",
    "newmsg.idle.border":     "rgba(216,138,31,0.48)",

    "user.bg":          "rgba(192,112,16,0.10)",
    "user.border":      "rgba(192,112,16,0.25)",
    "asst.bg":          "#EEF4FF",
    "asst.bg.top":      "#F6F9FF",
    "asst.bg.bottom":   "#E8F1FF",
    "asst.border":      "rgba(86,122,184,0.28)",
    "asst.line":        "rgba(86,122,184,0.95)",

    "state.success":    "#C07010",
    "state.successBg":  "rgba(192,112,16,0.12)",
    "state.warn":       "#D07010",
    "state.warnBg":     "rgba(208,112,16,0.10)",
    "state.error":      "#C03030",
    "state.errorBg":    "rgba(192,48,48,0.10)",

    "status.idle":      "#8888A0",
    "status.thinking":  "#4050D0",
    "status.responding":"#C07010",
    "status.error":     "#C03030",

    "selection":        "rgba(192,112,16,0.25)",
    "focusRing":        "rgba(192,112,16,0.60)",

    "scrollbar.track":  "rgba(0,0,0,0.07)",
    "scrollbar.thumb":  "rgba(0,0,0,0.22)",
    "scrollbar.hover":  "rgba(0,0,0,0.34)",

    "shadow.color":     "#000000",
    "shadow.ambient_alpha": 30,
    "shadow.key_alpha":     18,
}

if sys.platform == "darwin":
    _UI_FONT_CANDIDATES = (
        "SF Pro Text",
        "Helvetica Neue",
        "Helvetica",
        "Arial",
    )
    _MONO_FONT_CANDIDATES = (
        "SF Mono",
        "Menlo",
        "Monaco",
        "Courier New",
    )
elif sys.platform.startswith("linux"):
    _UI_FONT_CANDIDATES = (
        "Noto Sans",
        "Ubuntu",
        "Cantarell",
        "DejaVu Sans",
        "Arial",
    )
    _MONO_FONT_CANDIDATES = (
        "JetBrains Mono",
        "Noto Sans Mono",
        "Ubuntu Mono",
        "DejaVu Sans Mono",
        "Courier New",
    )
else:
    _UI_FONT_CANDIDATES = (
        "Segoe UI Variable",
        "Segoe UI",
        "Arial",
    )
    _MONO_FONT_CANDIDATES = (
        "Cascadia Mono",
        "Consolas",
        "Courier New",
    )


def _pick_font_family(candidates: tuple[str, ...], fallback: str) -> str:
    """Pick preferred font family without requiring an app instance."""
    return candidates[0] if candidates else fallback


def _to_qss_stack(candidates: tuple[str, ...], generic: str) -> str:
    """Build a Qt stylesheet-friendly fallback stack."""
    quoted = ", ".join(f"'{font}'" for font in candidates)
    return f"{quoted}, {generic}"


FONT_FAMILY_UI = _pick_font_family(_UI_FONT_CANDIDATES, _UI_FONT_CANDIDATES[0])
FONT_FAMILY_MONO = _pick_font_family(_MONO_FONT_CANDIDATES, _MONO_FONT_CANDIDATES[0])
FONT_STACK = _to_qss_stack(_UI_FONT_CANDIDATES, "sans-serif")
FONT_MONO = _to_qss_stack(_MONO_FONT_CANDIDATES, "monospace")



class ThemeManager:
    _mode:      str  = "dark"
    _callbacks: list = []
    _system_listener_attached: bool = False


    @classmethod
    def tokens(cls) -> dict:
        """Handle tokens."""
        return DARK_TOKENS if cls.current() == "dark" else LIGHT_TOKENS

    @classmethod
    def current(cls) -> str:
        """Handle current."""
        if cls._mode in ("dark", "light"):
            return cls._mode
        return cls._detect_system_theme()

    @classmethod
    def preference(cls) -> str:
        """Handle preference."""
        return cls._mode

    @classmethod
    def toggle(cls):
        """Toggle the state."""
        cls.set_theme("light" if cls.current() == "dark" else "dark")

    @classmethod
    def set_theme(cls, name: str):
        """Set theme."""
        assert name in ("dark", "light", "system")
        cls._mode = name
        QSettings("Quacky", "App").setValue("theme", name)
        cls._attach_system_theme_listener()
        cls._notify()

    @classmethod
    def load(cls):
        """Load state values."""
        mode = QSettings("Quacky", "App").value("theme", "dark")
        mode = str(mode) if mode is not None else "dark"
        if mode not in ("dark", "light", "system"):
            mode = "dark"
        cls._mode = mode
        cls._attach_system_theme_listener()

    @classmethod
    def subscribe(cls, callback):
        """Handle subscribe."""
        if callback not in cls._callbacks:
            cls._callbacks.append(callback)

    @classmethod
    def unsubscribe(cls, callback):
        """Handle unsubscribe."""
        cls._callbacks = [c for c in cls._callbacks if c is not callback]

    @classmethod
    def _notify(cls):
        """Handle notify."""
        t = cls.tokens()
        for cb in list(cls._callbacks):
            try:
                cb(t)
            except Exception:
                pass

    @classmethod
    def _attach_system_theme_listener(cls):
        """Handle attach system theme listener."""
        if cls._system_listener_attached:
            return
        app = QGuiApplication.instance()
        if app is None:
            return
        try:
            hints = app.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                hints.colorSchemeChanged.connect(cls._on_system_scheme_changed)
                cls._system_listener_attached = True
        except Exception:
            pass

    @classmethod
    def _on_system_scheme_changed(cls, *_args):
        """Handle system scheme changed callbacks."""
        if cls._mode == "system":
            cls._notify()

    @classmethod
    def _detect_system_theme(cls) -> str:
        """Handle detect system theme."""
        app = QGuiApplication.instance()
        if app is None:
            return "dark"

        try:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return "light"
            if scheme == Qt.ColorScheme.Dark:
                return "dark"
        except Exception:
            pass

        try:
            window_color = app.palette().color(QPalette.ColorRole.Window)
            return "dark" if window_color.lightness() < 128 else "light"
        except Exception:
            return "dark"
