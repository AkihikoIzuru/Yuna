"""Konfigurasi Jarvis - load .env dan validasi."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Konfigurasi utama aplikasi."""

    # 9Router
    base_url: str
    model: str
    fast_model: str
    api_key: str

    # Optional APIs
    openweather_api_key: Optional[str] = None
    weather_api_key: Optional[str] = None

    # Home Assistant (Fase 4)
    ha_url: Optional[str] = None
    ha_token: Optional[str] = None

    # Mikrotik (Fase 4)
    mikrotik_host: Optional[str] = None
    mikrotik_user: Optional[str] = None
    mikrotik_password: Optional[str] = None

    # Audio (Fase 2)
    whisper_model: str = "small"
    tts_voice: str = "id-ID-ArdiNeural"
    wake_word: str = "hey jarvis"
    audio_input_device: Optional[str] = None
    audio_output_device: Optional[str] = None

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        """Load konfigurasi dari .env."""
        if env_path is None:
            env_path = Path.cwd() / ".env"

        load_dotenv(env_path, override=True)

        # Required
        base_url = os.getenv("JARVIS_BASE_URL")
        model = os.getenv("JARVIS_MODEL")
        fast_model = os.getenv("JARVIS_FAST_MODEL")
        api_key = os.getenv("ROUTER_API_KEY")

        missing = []
        if not base_url:
            missing.append("JARVIS_BASE_URL")
        if not model:
            missing.append("JARVIS_MODEL")
        if not fast_model:
            missing.append("JARVIS_FAST_MODEL")
        if not api_key:
            missing.append("ROUTER_API_KEY")

        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")

        return cls(
            base_url=base_url,
            model=model,
            fast_model=fast_model,
            api_key=api_key,
            openweather_api_key=os.getenv("OPENWEATHER_API_KEY"),
            weather_api_key=os.getenv("WEATHER_API_KEY"),
            ha_url=os.getenv("HA_URL"),
            ha_token=os.getenv("HA_TOKEN"),
            mikrotik_host=os.getenv("MIKROTIK_HOST"),
            mikrotik_user=os.getenv("MIKROTIK_USER"),
            mikrotik_password=os.getenv("MIKROTIK_PASSWORD"),
            whisper_model=os.getenv("WHISPER_MODEL", "small"),
            tts_voice=os.getenv("TTS_VOICE", "id-ID-ArdiNeural"),
            wake_word=os.getenv("WAKE_WORD", "hey jarvis"),
            audio_input_device=os.getenv("AUDIO_INPUT_DEVICE"),
            audio_output_device=os.getenv("AUDIO_OUTPUT_DEVICE"),
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance (lazy load)."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reset_config() -> None:
    """Reset config (untuk testing)."""
    global _config
    _config = None