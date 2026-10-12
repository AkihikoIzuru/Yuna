"""App module untuk Yuna desktop."""

from yuna.app.tray import TrayApp, run_tray_app
from yuna.app.window import YunaWindow, run_window
from yuna.app.lifecycle import LifecycleManager, get_lifecycle, reset_lifecycle
from yuna.app.hotkeys import HotkeyManager, create_hotkey_manager
from yuna.app.notify import NotificationManager, get_notifier, notify, notify_reminder, notify_alert
from yuna.app.secrets import SecretManager, get_secret_manager, get_secret, set_secret
from yuna.app.autostart import (
    enable_autostart,
    disable_autostart,
    toggle_autostart,
    is_autostart_enabled,
)
from yuna.app.logging_setup import setup_logging, get_health_status, check_data_directory

__all__ = [
    "TrayApp",
    "run_tray_app",
    "YunaWindow",
    "run_window",
    "LifecycleManager",
    "get_lifecycle",
    "reset_lifecycle",
    "HotkeyManager",
    "create_hotkey_manager",
    "NotificationManager",
    "get_notifier",
    "notify",
    "notify_reminder",
    "notify_alert",
    "SecretManager",
    "get_secret_manager",
    "get_secret",
    "set_secret",
    "enable_autostart",
    "disable_autostart",
    "toggle_autostart",
    "is_autostart_enabled",
    "setup_logging",
    "get_health_status",
    "check_data_directory",
]
