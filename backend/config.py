# backend/config.py
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


@dataclass(frozen=True)
class Settings:
    api_key: str
    model_name: str
    port: int


def get_settings() -> Settings:
    if load_dotenv:
        load_dotenv()

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    port = int(os.getenv("PORT", "8000"))

    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")

    return Settings(
        api_key=api_key,
        model_name=model_name,
        port=port,
    )
