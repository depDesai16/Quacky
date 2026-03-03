"""
theme.py — ThemeManager + design tokens for Quacky UI.
All colors are defined here; nothing else in the codebase should
hardcode a color value.
"""

import sys

from PyQt6.QtCore import QSettings


DARK_TOKENS: dict = {
    "bg.canvas":        "#141414",
    "bg.surface":       "#1C1C1C",
    "bg.elevated":      "#242424",

    "text.primary":     "#E8E8F0",
    "text.secondary":   "#9090A8",
    "text.muted":       "#55556A",

    "border.subtle":    "rgba(255,255,255,0.08)",
    "border.strong":    "rgba(255,255,255,0.16)",

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

    "state.success":    "#34C77B",
    "state.successBg":  "rgba(52,199,123,0.12)",
    "state.warn":       "#F0A030",
    "state.warnBg":     "rgba(240,160,48,0.12)",
    "state.error":      "#E05555",
    "state.errorBg":    "rgba(224,85,85,0.12)",

    "status.idle":      "#5A5A7A",
    "status.thinking":  "#7A8AFF",
    "status.responding":"#34C77B",
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

    "text.primary":     "#18181E",
    "text.secondary":   "#606070",
    "text.muted":       "#A0A0B0",

    "border.subtle":    "rgba(0,0,0,0.07)",
    "border.strong":    "rgba(0,0,0,0.14)",

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

    "state.success":    "#1E9F5E",
    "state.successBg":  "rgba(30,159,94,0.10)",
    "state.warn":       "#D07010",
    "state.warnBg":     "rgba(208,112,16,0.10)",
    "state.error":      "#C03030",
    "state.errorBg":    "rgba(192,48,48,0.10)",

    "status.idle":      "#8888A0",
    "status.thinking":  "#4050D0",
    "status.responding":"#1E9F5E",
    "status.error":     "#C03030",

    "selection":        "rgba(192,112,16,0.25)",
    "focusRing":        "rgba(192,112,16,0.60)",

    "scrollbar.track":  "rgba(0,0,0,0.04)",
    "scrollbar.thumb":  "rgba(0,0,0,0.14)",
    "scrollbar.hover":  "rgba(0,0,0,0.24)",

    "shadow.color":     "#000000",
    "shadow.ambient_alpha": 30,
    "shadow.key_alpha":     18,
}

if sys.platform == "darwin":
    FONT_FAMILY_UI = "SF Pro Text"
    FONT_STACK = "'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', 'Arial', sans-serif"
    FONT_FAMILY_MONO = "SF Mono"
    FONT_MONO = "'SF Mono', 'Menlo', 'Monaco', 'DejaVu Sans Mono', monospace"
elif sys.platform.startswith("linux"):
    FONT_FAMILY_UI = "Noto Sans"
    FONT_STACK = "'Noto Sans', 'Inter', 'Ubuntu', 'Cantarell', 'DejaVu Sans', sans-serif"
    FONT_FAMILY_MONO = "DejaVu Sans Mono"
    FONT_MONO = "'JetBrains Mono', 'Noto Sans Mono', 'DejaVu Sans Mono', monospace"
else:
    FONT_FAMILY_UI = "Segoe UI"
    FONT_STACK = "'Segoe UI Variable', 'Segoe UI', 'Inter', 'Arial', sans-serif"
    FONT_FAMILY_MONO = "Cascadia Code"
    FONT_MONO = "'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace"



class ThemeManager:
    """
    Singleton-style theme manager.
    Call ThemeManager.subscribe(callback) to receive token dicts on change.
    """
    _current:   str  = "dark"
    _callbacks: list = []


    @classmethod
    def tokens(cls) -> dict:
        return DARK_TOKENS if cls._current == "dark" else LIGHT_TOKENS

    @classmethod
    def current(cls) -> str:
        return cls._current

    @classmethod
    def toggle(cls):
        cls.set_theme("light" if cls._current == "dark" else "dark")

    @classmethod
    def set_theme(cls, name: str):
        assert name in ("dark", "light")
        cls._current = name
        QSettings("Quacky", "App").setValue("theme", name)
        t = cls.tokens()
        for cb in list(cls._callbacks):
            try:
                cb(t)
            except Exception:
                pass

    @classmethod
    def load(cls):
        """Call once at startup to restore persisted theme."""
        cls._current = QSettings("Quacky", "App").value("theme", "dark")

    @classmethod
    def subscribe(cls, callback):
        """Register callable(tokens: dict) called on every theme change."""
        if callback not in cls._callbacks:
            cls._callbacks.append(callback)

    @classmethod
    def unsubscribe(cls, callback):
        cls._callbacks = [c for c in cls._callbacks if c is not callback]
