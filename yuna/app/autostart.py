"""Auto-start management untuk Windows."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Registry path untuk auto-start
AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "yuna"


def get_executable_path() -> Path:
    """Get path ke executable (python script atau .exe)."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        return Path(sys.executable)
    else:
        # Running as Python script
        # Return path to main.py
        return Path.cwd() / "yuna" / "main.py"


def get_startup_args(minimized: bool = True) -> str:
    """Get command line arguments untuk auto-start."""
    args = []
    if minimized:
        args.append("--minimized")
    return " ".join(args)


def is_autostart_enabled() -> bool:
    """Cek apakah auto-start sudah diaktifkan."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_KEY,
            0,
            winreg.KEY_READ
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def enable_autostart(minimized: bool = True) -> bool:
    """Aktifkan auto-start saat Windows boot."""
    try:
        import winreg

        exe_path = get_executable_path()
        args = get_startup_args(minimized)

        if exe_path.suffix == ".exe":
            command = f'"{exe_path}" {args}'
        else:
            # Python script
            python_exe = Path(sys.executable)
            command = f'"{python_exe}" "{exe_path}" {args}'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_KEY,
            0,
            winreg.KEY_WRITE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        logger.info(f"Auto-start enabled: {command}")
        return True

    except Exception as e:
        logger.error(f"Failed to enable auto-start: {e}")
        return False


def disable_autostart() -> bool:
    """Nonaktifkan auto-start."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_KEY,
            0,
            winreg.KEY_WRITE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)

        logger.info("Auto-start disabled")
        return True

    except (FileNotFoundError, OSError):
        logger.warning("Auto-start not enabled")
        return True
    except Exception as e:
        logger.error(f"Failed to disable auto-start: {e}")
        return False


def toggle_autostart(minimized: bool = True) -> bool:
    """Toggle auto-start on/off."""
    if is_autostart_enabled():
        return disable_autostart()
    else:
        return enable_autostart(minimized)


def get_autostart_command() -> Optional[str]:
    """Get current auto-start command."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            AUTOSTART_KEY,
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return value
    except (FileNotFoundError, OSError):
        return None
