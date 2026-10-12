"""Logging setup dengan rotasi dan secret masking."""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Sensitive keys yang tidak boleh muncul di log
SENSITIVE_KEYS = {
    "API_KEY", "TOKEN", "PASSWORD", "PASS", "SECRET",
    "ROUTER_API_KEY", "HA_TOKEN", "MIKROTIK_PASSWORD",
    "MQTT_PASSWORD", "OPENWEATHER_API_KEY", "WEATHER_API_KEY",
    "PORCUPINE_ACCESS_KEY",
}


def mask_sensitive(value: str) -> str:
    """Mask nilai sensitif untuk logging."""
    if not value or len(value) < 6:
        return "***"
    return value[:4] + "****" + value[-2:]


def get_log_dir() -> Path:
    """Get log directory, default ke %APPDATA%\\Yuna\\logs."""
    from yuna.config import get_config
    config = get_config()
    if config.log_dir:
        return Path(config.log_dir)
    return Path.home() / "AppData" / "Roaming" / "yuna" / "logs"


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    max_bytes: int = 2 * 1024 * 1024,  # 2 MB per file
    backup_count: int = 5,
) -> logging.Logger:
    """
    Setup logging dengan rotasi file.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Simpan log ke file
        max_bytes: Ukuran maksimal per file log
        backup_count: Jumlah file backup

    Returns:
        Root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Format
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler dengan rotasi
    if log_to_file:
        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file
        log_file = log_dir / "yuna.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Audit log (tool calls)
        audit_file = log_dir / "audit.log"
        audit_handler = logging.handlers.RotatingFileHandler(
            audit_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        audit_handler.setFormatter(formatter)
        root_logger.addHandler(audit_handler)

        logger.info(f"Logging setup: level={level}, dir={log_dir}")

    return root_logger


def mask_log_message(message: str) -> str:
    """
    Mask sensitive values in log message.

    Args:
        message: Log message

    Returns:
        Message dengan nilai sensitif di-mask
    """
    import re
    for key in SENSITIVE_KEYS:
        # Pattern: KEY=value atau KEY: value
        pattern = rf'({key}[=:]\s*)(\S+)'
        message = re.sub(pattern, lambda m: m.group(1) + mask_sensitive(m.group(2)), message, flags=re.IGNORECASE)
    return message


def get_health_status() -> dict:
    """
    Get health status untuk berbagai komponen.

    Returns:
        Dict dengan status kesehatan setiap komponen
    """
    import sys
    from pathlib import Path
    import socket
    import platform

    status = {
        "system": {
            "healthy": True,
            "detail": f"{platform.system()} {platform.release()}",
        },
        "python": {
            "healthy": True,
            "detail": sys.version.split()[0],
        },
        "9router": {
            "healthy": True,
            "detail": "Checking...",
        },
        "homeassistant": {
            "healthy": True,
            "detail": "Not configured",
        },
        "mikrotik": {
            "healthy": True,
            "detail": "Not configured",
        },
        "voice": {
            "healthy": True,
            "detail": "Ready",
        },
        "data_dir": {
            "healthy": True,
            "detail": str(Path.home()),
        },
    }

    # Check 9Router connectivity
    try:
        from yuna.config import get_config
        config = get_config()
        import urllib.request
        url = f"{config.base_url}/models"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {config.api_key}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                status["9router"]["detail"] = "OK"
                status["9router"]["healthy"] = True
            else:
                status["9router"]["detail"] = f"HTTP {resp.status}"
                status["9router"]["healthy"] = False
    except Exception as e:
        status["9router"]["detail"] = str(e)[:50]
        status["9router"]["healthy"] = False

    # Check Home Assistant
    try:
        from yuna.config import get_config
        config = get_config()
        if config.ha_url and config.ha_token:
            import urllib.request
            url = f"{config.ha_url}/api/"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {config.ha_token}",
                "X-HA-Access": config.ha_token,
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    status["homeassistant"]["detail"] = "Connected"
                    status["homeassistant"]["healthy"] = True
                else:
                    status["homeassistant"]["detail"] = f"HTTP {resp.status}"
                    status["homeassistant"]["healthy"] = False
    except Exception:
        status["homeassistant"]["healthy"] = False

    # Check MikroTik
    try:
        from yuna.config import get_config
        config = get_config()
        if config.mikrotik_host:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((config.mikrotik_host, 8728))
            sock.close()
            status["mikrotik"]["detail"] = "Connected"
            status["mikrotik"]["healthy"] = True
    except Exception:
        status["mikrotik"]["healthy"] = False

    # Check data directory
    try:
        data_dir = Path.home() / "AppData" / "Roaming" / "yuna"
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".healthcheck"
        test_file.write_text("ok")
        test_file.unlink()
        status["data_dir"]["detail"] = str(data_dir)
    except Exception as e:
        status["data_dir"]["healthy"] = False
        status["data_dir"]["detail"] = str(e)

    return status


def check_data_directory() -> bool:
    """
    Verify data directory exists and is writable.

    Returns:
        True if data directory is accessible
    """
    try:
        data_dir = Path.home() / "AppData" / "Roaming" / "yuna"
        data_dir.mkdir(parents=True, exist_ok=True)
        # Test write
        test_file = data_dir / ".healthcheck"
        test_file.write_text("ok")
        test_file.unlink()
        return True
    except Exception as e:
        logger.error(f"Data directory check failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_logging()
    print("Logging setup OK")
    health = get_health_status()
    print(f"Health: {health}")

