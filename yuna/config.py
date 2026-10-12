"""Konfigurasi Yuna - load .env dan validasi."""

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

    # Identity
    assistant_name: str = "Yuna"
    assistant_fullname: str = "Your Unified Network Assistant"
    project_codename: str = "Project Hearth"
    assistant_id: str = "YNA-HRT-001"
    user_nickname: str = "Kak Akii"

    # Audio (Fase 2)
    whisper_model: str = "small"
    tts_voice: str = "id-ID-GadisNeural"
    tts_rate: str = "+3%"
    tts_pitch: str = "+3Hz"
    wake_word: str = "hey yuna"
    wake_backend: str = "auto"  # auto, whisper, porcupine, openwakeword
    wake_phrases: Optional[str] = None  # comma-separated
    audio_input_device: Optional[str] = None
    audio_output_device: Optional[str] = None

    # Desktop App (Fase 7)
    data_dir: Optional[str] = None  # %APPDATA%\Yuna
    log_dir: Optional[str] = None   # %APPDATA%\Yuna\logs
    ui_host: str = "127.0.0.1"
    ui_port: int = 8080
    auto_start: bool = False
    tray_tooltip: str = "Yuna"

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        """Load konfigurasi dari .env."""
        if env_path is None:
            env_path = Path.cwd() / ".env"

        load_dotenv(env_path, override=True)

        # Log fallback warning for old JARVIS_* variables
        import logging
        logger = logging.getLogger(__name__)
        fallback_vars = {
            "JARVIS_BASE_URL": "YUNA_BASE_URL",
            "JARVIS_MODEL": "YUNA_MODEL",
            "JARVIS_FAST_MODEL": "YUNA_FAST_MODEL",
            "JARVIS_HA_URL": "YUNA_HA_URL",
            "JARVIS_HA_TOKEN": "YUNA_HA_TOKEN",
            "JARVIS_MIKROTIK_HOST": "YUNA_MIKROTIK_HOST",
            "JARVIS_MIKROTIK_USER": "YUNA_MIKROTIK_USER",
            "JARVIS_MIKROTIK_PASSWORD": "YUNA_MIKROTIK_PASSWORD",
        }
        for old_key, new_key in fallback_vars.items():
            if os.getenv(old_key) and not os.getenv(new_key):
                logger.warning(f"Env var {old_key} diganti ke {new_key}: {os.getenv(old_key)}")
                os.environ[new_key] = os.getenv(old_key)

        # Required
        base_url = os.getenv("YUNA_BASE_URL")
        model = os.getenv("YUNA_MODEL")
        fast_model = os.getenv("YUNA_FAST_MODEL")
        api_key = os.getenv("ROUTER_API_KEY")

        missing = []
        if not base_url:
            missing.append("YUNA_BASE_URL")
        if not model:
            missing.append("YUNA_MODEL")
        if not fast_model:
            missing.append("YUNA_FAST_MODEL")
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
            ha_url=os.getenv("YUNA_HA_URL"),
            ha_token=os.getenv("YUNA_HA_TOKEN"),
            mikrotik_host=os.getenv("YUNA_MIKROTIK_HOST"),
            mikrotik_user=os.getenv("YUNA_MIKROTIK_USER"),
            mikrotik_password=os.getenv("YUNA_MIKROTIK_PASSWORD"),
            assistant_name=os.getenv("ASSISTANT_NAME", "Yuna"),
            assistant_fullname=os.getenv("ASSISTANT_FULLNAME", "Your Unified Network Assistant"),
            project_codename=os.getenv("PROJECT_CODENAME", "Project Hearth"),
            assistant_id=os.getenv("ASSISTANT_ID", "YNA-HRT-001"),
            user_nickname=os.getenv("USER_NICKNAME", "Kak Akii"),
            whisper_model=os.getenv("WHISPER_MODEL", "small"),
            tts_voice=os.getenv("TTS_VOICE", "id-ID-GadisNeural"),
            tts_rate=os.getenv("TTS_RATE", "+3%"),
            tts_pitch=os.getenv("TTS_PITCH", "+3Hz"),
            wake_word=os.getenv("WAKE_WORD", "hey yuna"),
            wake_backend=os.getenv("WAKE_BACKEND", "auto"),
            wake_phrases=os.getenv("WAKE_PHRASES", "yuna,yu na,yuuna,juna,yona,una"),
            audio_input_device=os.getenv("AUDIO_INPUT_DEVICE"),
            audio_output_device=os.getenv("AUDIO_OUTPUT_DEVICE"),
            data_dir=os.getenv("DATA_DIR"),
            log_dir=os.getenv("LOG_DIR"),
            ui_host=os.getenv("UI_HOST", "127.0.0.1"),
            ui_port=int(os.getenv("UI_PORT", "8080")),
            auto_start=os.getenv("AUTO_START", "false").lower() == "true",
            tray_tooltip=os.getenv("TRAY_TOOLTIP", "Yuna"),
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
