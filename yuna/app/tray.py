"""System Tray untuk Yuna menggunakan pystray."""

import sys
import threading
import logging
from pathlib import Path
from typing import Callable, Optional

import pystray
from PIL import Image

from yuna.app.icons import create_tray_icon, STATUS_COLORS
from yuna.config import get_config

logger = logging.getLogger(__name__)


class TrayApp:
    """System tray application untuk Yuna."""

    def __init__(self):
        self._icon: Optional[pystray.Icon] = None
        self._running = False
        self._callbacks = {}
        self._current_status = "idle"
        self._muted = False
        self._wake_mode = True  # True = wake word, False = PTT

        # Config
        config = get_config()
        self._assistant_name = "yuna"

    def set_callback(self, name: str, callback: Callable):
        """Set callback untuk action."""
        self._callbacks[name] = callback

    def get_callback(self, name: str) -> Optional[Callable]:
        """Get callback."""
        return self._callbacks.get(name)

    def run(self):
        """Jalankan system tray (blocking)."""
        self._running = True

        # Create initial icon
        icon_image = create_tray_icon("idle", 64)

        # Build menu
        menu = self._build_menu()

        # Create pystray icon
        self._icon = pystray.Icon(
            "yuna",
            icon_image,
            self._assistant_name,
            menu,
        )

        # Setup click handlers
        self._icon.on_click = self._on_click

        logger.info("Starting system tray...")
        self._icon.run()

    def _build_menu(self) -> pystray.Menu:
        """Build tray menu."""
        def make_callback(action_name: str):
            def callback(icon, item):
                cb = self.get_callback(action_name)
                if cb:
                    cb()
            return callback

        def make_toggle(action_name: str, get_state: Callable):
            def callback(icon, item):
                cb = self.get_callback(action_name)
                if cb:
                    cb()
            # We'll update checked state via item
            return callback

        # Build menu items
        items = [
            pystray.MenuItem("Buka Jendela", make_callback("show_window"), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Mikrofon", pystray.Menu(
                pystray.MenuItem("Nyala", make_callback("mic_on")),
                pystray.MenuItem("Mati", make_callback("mic_off")),
            )),
            pystray.MenuItem("Mode", pystray.Menu(
                pystray.MenuItem("Wake Word", make_callback("mode_wake"),
                              checked=lambda item: self._wake_mode),
                pystray.MenuItem("Push-to-Talk", make_callback("mode_ptt"),
                              checked=lambda item: not self._wake_mode),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Status", pystray.Menu(
                pystray.MenuItem("9Router: Cek...", None, enabled=False),
                pystray.MenuItem("MikroTik: Cek...", None, enabled=False),
            )),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pengaturan", make_callback("open_settings")),
            pystray.MenuItem("Buka Folder Log", make_callback("open_log_folder")),
            pystray.MenuItem("Auto-start Windows", make_callback("toggle_autostart"),
                           checked=lambda item: self._is_autostart_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Keluar", make_callback("quit")),
        ]

        return pystray.Menu(*items)

    def _on_click(self, icon, button, time):
        """Handle tray icon click."""
        if button == pystray.MouseButton.left:
            cb = self.get_callback("show_window")
            if cb:
                cb()

    def update_status(self, status: str):
        """Update tray icon status."""
        if not self._running or not self._icon:
            return

        self._current_status = status
        try:
            new_image = create_tray_icon(status, 64)
            self._icon.icon = new_image
            self._icon.title = f"{self._assistant_name} - {status.upper()}"
        except Exception as e:
            logger.error(f"Failed to update tray icon: {e}")

    def set_muted(self, muted: bool):
        """Set mute status."""
        self._muted = muted
        if muted:
            self.update_status("muted")

    def set_wake_mode(self, wake: bool):
        """Set wake mode."""
        self._wake_mode = wake
        # Rebuild menu to update checked states
        if self._icon:
            self._icon.menu = self._build_menu()

    def update_connection_status(self, router_ok: bool, mikrotik_ok: bool):
        """Update connection status in menu."""
        if self._icon:
            self._icon.menu = self._build_menu()

    def _is_autostart_enabled(self) -> bool:
        """Check if auto-start is enabled."""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            winreg.QueryValueEx(key, "yuna")
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            return False

    def stop(self):
        """Stop tray app."""
        self._running = False
        if self._icon:
            self._icon.stop()
        logger.info("System tray stopped")


def run_tray_app(callbacks: dict = None) -> TrayApp:
    """
    Run tray app in background thread.

    Args:
        callbacks: Dict of callback functions
            - show_window: Open main window
            - mic_on/off: Toggle mic
            - mode_wake/ptt: Change mode
            - open_settings: Open settings
            - open_log_folder: Open log folder
            - toggle_autostart: Toggle auto-start
            - quit: Quit application

    Returns:
        TrayApp instance
    """
    tray = TrayApp()

    if callbacks:
        for name, cb in callbacks.items():
            tray.set_callback(name, cb)

    # Run in background thread
    thread = threading.Thread(target=tray.run, daemon=True)
    thread.start()

    return tray


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)

    def test_cb(name):
        print(f"Callback: {name}")

    callbacks = {
        "show_window": lambda: test_cb("show_window"),
        "mic_on": lambda: test_cb("mic_on"),
        "mic_off": lambda: test_cb("mic_off"),
        "mode_wake": lambda: test_cb("mode_wake"),
        "mode_ptt": lambda: test_cb("mode_ptt"),
        "open_settings": lambda: test_cb("open_settings"),
        "open_log_folder": lambda: test_cb("open_log_folder"),
        "toggle_autostart": lambda: test_cb("toggle_autostart"),
        "quit": lambda: test_cb("quit"),
    }

    tray = run_tray_app(callbacks)

    # Keep alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tray.stop()
