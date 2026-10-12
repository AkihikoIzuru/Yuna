"""Main entrypoint untuk Yuna Desktop App."""

import asyncio
import logging
import sys
import threading
import time
from pathlib import Path

from yuna.app import (
    get_lifecycle,
    run_tray_app,
    run_window,
    get_notifier,
    create_hotkey_manager,
)
from yuna.config import get_config
from yuna.brain.agent import get_agent
from yuna.memory import ConversationHistory, ReminderManager
from yuna.ui.server import app as ui_app, notify_status_change, notify_transcript, notify_tool_call, notify_tool_result
from yuna.voice.loop import run_voice_loop

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class YunaApp:
    """Main Yuna Desktop Application."""

    def __init__(self):
        self.lifecycle = get_lifecycle()
        self.tray = None
        self.window = None
        self.hotkeys = None
        self.notifier = None
        self.voice_thread = None
        self.ui_thread = None
        self._running = False
        self._muted = False
        self._wake_mode = True

    def setup_callbacks(self):
        """Setup all callbacks."""
        # Lifecycle callbacks
        self.lifecycle.add_startup_callback(self._on_startup)
        self.lifecycle.add_shutdown_callback(self._on_shutdown)
        self.lifecycle.add_health_check(self._health_check)

        # Tray callbacks
        tray_callbacks = {
            "show_window": self.show_window,
            "mic_on": self.mic_on,
            "mic_off": self.mic_off,
            "mode_wake": self.set_wake_mode_true,
            "mode_ptt": self.set_wake_mode_false,
            "open_settings": self.open_settings,
            "open_log_folder": self.open_log_folder,
            "toggle_autostart": self.toggle_autostart,
            "quit": self.quit,
        }

        # Hotkey callbacks
        hotkey_callbacks = {
            "show_hide_window": ("ctrl+alt+j", "Show/hide window", self.toggle_window),
            "push_to_talk": ("space", "Push-to-talk", self.start_ptt),
            "mute_toggle": ("ctrl+alt+m", "Toggle mute", self.toggle_mute),
            "mode_toggle": ("ctrl+alt+w", "Toggle mode", self.toggle_mode),
        }

        # Start tray
        self.tray = run_tray_app(tray_callbacks)

        # Start hotkeys
        self.hotkeys = create_hotkey_manager(hotkey_callbacks)
        self.hotkeys.start()

        # Notifier
        self.notifier = get_notifier()

        # Setup UI callbacks
        from yuna.ui.server import (
            set_status, notify_status_change as ui_notify_status,
            notify_transcript as ui_notify_transcript,
            notify_tool_call as ui_notify_tool_call,
            notify_tool_result as ui_notify_tool_result,
        )
        # These are already available as module functions

    def _on_startup(self):
        """Startup callback."""
        logger.info("yuna starting up...")
        self.notifier.show("yuna", "Asisten AI rumah siap!")

        # Start UI server in background
        self.ui_thread = threading.Thread(target=self._run_ui_server, daemon=True)
        self.ui_thread.start()

        # Start voice loop in background
        self.voice_thread = threading.Thread(target=self._run_voice_loop, daemon=True)
        self.voice_thread.start()

    def _on_shutdown(self):
        """Shutdown callback."""
        logger.info("yuna shutting down...")
        self.notifier.show("yuna", "Sampai jumpa!")
        if self.hotkeys:
            self.hotkeys.stop()
        if self.tray:
            self.tray.stop()

    def _health_check(self):
        """Health check callback."""
        config = get_config()
        return f"Model: {config.model}, 9Router: {config.base_url}"

    def _run_ui_server(self):
        """Run FastAPI UI server."""
        import uvicorn
        uvicorn.run(ui_app, host="127.0.0.1", port=8080, log_level="warning")

    def _run_voice_loop(self):
        """Run voice loop."""
        # Wait a bit for UI server to start
        time.sleep(2)
        try:
            asyncio.run(run_voice_loop(mode="wake" if self._wake_mode else "push"))
        except Exception as e:
            logger.error(f"Voice loop error: {e}")

    def show_window(self):
        """Show main window."""
        if self.window is None:
            self.window = run_window(url="http://localhost:8080", on_close=self.hide_window)
        else:
            self.window.show()

    def hide_window(self):
        """Hide main window."""
        if self.window:
            self.window.hide()

    def toggle_window(self):
        """Toggle window visibility."""
        if self.window and self.window.is_visible():
            self.hide_window()
        else:
            self.show_window()

    def mic_on(self):
        """Turn mic on."""
        self._muted = False
        if self.tray:
            self.tray.set_muted(False)
        self.notifier.show("Mikrofon", "Mikrofon dinyalakan")

    def mic_off(self):
        """Turn mic off."""
        self._muted = True
        if self.tray:
            self.tray.set_muted(True)
        self.notifier.show("Mikrofon", "Mikrofon dimatikan")

    def toggle_mute(self):
        """Toggle mute."""
        if self._muted:
            self.mic_on()
        else:
            self.mic_off()

    def set_wake_mode_true(self):
        """Set wake word mode."""
        self._wake_mode = True
        if self.tray:
            self.tray.set_wake_mode(True)
        self.notifier.show("Mode", "Wake word mode aktif")

    def set_wake_mode_false(self):
        """Set PTT mode."""
        self._wake_mode = False
        if self.tray:
            self.tray.set_wake_mode(False)
        self.notifier.show("Mode", "Push-to-talk mode aktif")

    def toggle_mode(self):
        """Toggle wake/PTT mode."""
        if self._wake_mode:
            self.set_wake_mode_false()
        else:
            self.set_wake_mode_true()

    def start_ptt(self):
        """Start push-to-talk (hold)."""
        if not self._muted and not self._wake_mode:
            # In PTT mode, space key starts recording
            notify_status_change("listening")
            notify_transcript("Mendengarkan...")

    def open_settings(self):
        """Open settings window."""
        # TODO: Implement settings dialog
        self.notifier.show("Pengaturan", "Belum diimplementasikan")

    def open_log_folder(self):
        """Open log folder."""
        import subprocess
        log_dir = Path.home() / "AppData" / "Roaming" / "yuna" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer "{log_dir}"')

    def toggle_autostart(self):
        """Toggle auto-start."""
        from yuna.app import toggle_autostart
        enabled = toggle_autostart()
        status = "diaktifkan" if enabled else "dinonaktifkan"
        self.notifier.show("Auto-start", f"Auto-start {status}")

    def quit(self):
        """Quit application."""
        self.lifecycle.shutdown()


def main():
    """Main entry point."""
    # Check single instance
    lifecycle = get_lifecycle()
    if not lifecycle.start():
        print("yuna sudah berjalan!")
        sys.exit(1)

    # Create app
    app = YunaApp()
    app.setup_callbacks()

    # Show window on startup
    app.show_window()

    # Wait for shutdown
    lifecycle.wait_for_shutdown()


if __name__ == "__main__":
    main()
