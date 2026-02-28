"""
Shared assistant identity configuration.

Environment variables:
- QUACKY_ASSISTANT_NAME: display/identity name, default "Quacky"
- QUACKY_WAKE_WORDS: comma-separated wake phrases, default derived from name
"""
from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


DEFAULT_ASSISTANT_NAME = "Quacky"


def _normalize_phrase(text: str) -> str:
    """Lowercase and collapse extra whitespace in a phrase."""
    return " ".join(text.strip().lower().split())


def _dedupe_keep_order(items: list[str]) -> list[str]:
    """Remove duplicates while preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def get_assistant_name() -> str:
    """Read assistant name from env, falling back to the default name."""
    if load_dotenv:
        load_dotenv()
    raw = os.getenv("QUACKY_ASSISTANT_NAME", DEFAULT_ASSISTANT_NAME).strip()
    return raw or DEFAULT_ASSISTANT_NAME


def get_wake_words(assistant_name: str | None = None) -> list[str]:
    """Return wake words from env or derive defaults from assistant name."""
    if load_dotenv:
        load_dotenv()

    name = (assistant_name or get_assistant_name()).strip()
    name_lower = _normalize_phrase(name)

    env_words = os.getenv("QUACKY_WAKE_WORDS", "").strip()
    if env_words:
        parsed = [_normalize_phrase(part) for part in env_words.split(",")]
        parsed = _dedupe_keep_order([p for p in parsed if p])
        if parsed:
            return parsed

    defaults = [f"hey {name_lower}", name_lower]
    if name_lower == "quacky":
        defaults.extend(["hey quaky", "hey ducky"])
    return _dedupe_keep_order(defaults)
