"""Global hotkeys menggunakan pynput."""

import logging
import threading
from typing import Callable, Dict, Optional

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Manage global hotkeys."""

    def __init__(self):
        self._hotkeys: Dict[str, Callable] = {}
        self._pressed_keys: set = set()
        self._listener: Optional[keyboard.Listener] = None
        self._running = False

    def register(self, key_combo: str, callback: Callable, description: str = ""):
        """
        Register a hotkey.

        Args:
            key_combo: Key combination like "ctrl+alt+j", "f1", "shift+space"
            callback: Function to call when hotkey pressed
            description: Description for logging
        """
        self._hotkeys[key_combo.lower()] = {
            "callback": callback,
            "description": description,
            "keys": self._parse_combo(key_combo),
        }
        logger.info(f"Registered hotkey: {key_combo} - {description}")

    def _parse_combo(self, combo: str) -> set:
        """Parse key combination string to set of key names."""
        parts = combo.lower().split("+")
        keys = set()
        for part in parts:
            part = part.strip()
            # Normalize key names
            if part in ("ctrl", "control"):
                keys.add("ctrl")
            elif part in ("alt", "option"):
                keys.add("alt")
            elif part in ("shift",):
                keys.add("shift")
            elif part in ("cmd", "win", "super", "windows"):
                keys.add("cmd")
            elif len(part) == 1:
                keys.add(part)
            else:
                keys.add(part)
        return keys

    def _on_press(self, key):
        """Handle key press."""
        try:
            key_str = self._key_to_str(key)
            self._pressed_keys.add(key_str)
            self._check_hotkeys()
        except Exception as e:
            logger.debug(f"Key press error: {e}")

    def _on_release(self, key):
        """Handle key release."""
        try:
            key_str = self._key_to_str(key)
            self._pressed_keys.discard(key_str)
        except Exception as e:
            logger.debug(f"Key release error: {e}")

    def _key_to_str(self, key) -> str:
        """Convert pynput key to string."""
        if hasattr(key, 'char') and key.char:
            return key.char.lower()
        elif hasattr(key, 'name'):
            name = key.name.lower()
            # Normalize
            if name in ("ctrl_l", "ctrl_r"):
                return "ctrl"
            elif name in ("alt_l", "alt_r"):
                return "alt"
            elif name in ("shift_l", "shift_r"):
                return "shift"
            elif name in ("cmd_l", "cmd_r", "win_l", "win_r"):
                return "cmd"
            return name
        return str(key).lower()

    def _check_hotkeys(self):
        """Check if any registered hotkey matches current pressed keys."""
        for combo, info in self._hotkeys.items():
            if info["keys"].issubset(self._pressed_keys):
                # Execute callback in separate thread to avoid blocking listener
                threading.Thread(target=info["callback"], daemon=True).start()
                # Clear to prevent repeated firing
                self._pressed_keys.clear()
                break

    def start(self):
        """Start listening for hotkeys."""
        if self._running:
            return

        self._running = True
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info("Hotkey listener started")

    def stop(self):
        """Stop listening for hotkeys."""
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        logger.info("Hotkey listener stopped")


# Default hotkeys
DEFAULT_HOTKEYS = {
    "show_hide_window": ("ctrl+alt+j", "Show/hide main window"),
    "push_to_talk": ("space", "Push-to-talk (hold)"),
    "mute_toggle": ("ctrl+alt+m", "Toggle mute"),
    "mode_toggle": ("ctrl+alt+w", "Toggle wake/PTT mode"),
}


def create_hotkey_manager(custom_hotkeys: dict = None) -> HotkeyManager:
    """
    Create and configure hotkey manager with default + custom hotkeys.

    Args:
        custom_hotkeys: Dict of {action_name: (key_combo, description, callback)}

    Returns:
        Configured HotkeyManager
    """
    manager = HotkeyManager()

    # Register custom hotkeys
    if custom_hotkeys:
        for action_name, (combo, description, callback) in custom_hotkeys.items():
            manager.register(combo, callback, description)

    return manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def test_show():
        print("Show/hide window!")

    def test_ptt():
        print("PTT activated!")

    def test_mute():
        print("Mute toggled!")

    def test_mode():
        print("Mode toggled!")

    custom = {
        "show_hide_window": ("ctrl+alt+j", "Show/hide window", test_show),
        "push_to_talk": ("space", "Push-to-talk", test_ptt),
        "mute_toggle": ("ctrl+alt+m", "Toggle mute", test_mute),
        "mode_toggle": ("ctrl+alt+w", "Toggle mode", test_mode),
    }

    manager = create_hotkey_manager(custom)
    manager.start()

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop()