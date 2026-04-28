# backend/config.py
import os
from dataclasses import dataclass

from backend.core.app_paths import resource_path
from backend.core.settings_service import get_api_key as get_saved_api_key

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


@dataclass
class Settings:
    api_key: str
    model_name: str
    port: int
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    tts_default_enabled: bool


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    if load_dotenv:
        load_dotenv(resource_path("config.env"))

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or get_saved_api_key()
    )
    port = int(os.getenv("PORT", "8000"))
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    elevenlabs_model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
    tts_default_enabled = _as_bool(os.getenv("TTS_DEFAULT_ENABLED"), default=False)

    return Settings(
        api_key=api_key or "",
        model_name=model_name,
        port=port,
        elevenlabs_api_key=elevenlabs_api_key,
        elevenlabs_voice_id=elevenlabs_voice_id,
        elevenlabs_model_id=elevenlabs_model_id,
        tts_default_enabled=tts_default_enabled,
    )
