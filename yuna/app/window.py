"""Main window menggunakan pywebview."""

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class YunaWindow:
    """Main application window menggunakan pywebview."""

    def __init__(
        self,
        url: str = "http://localhost:8080",
        title: str = "yuna",
        width: int = 1200,
        height: int = 800,
        on_close: Optional[Callable] = None,
    ):
        self.url = url
        self.title = title
        self.width = width
        self.height = height
        self.on_close = on_close
        self._window = None
        self._webview = None
        self._visible = False

    def create(self):
        """Create window (must be called from main thread)."""
        try:
            import webview
            self._webview = webview

            self._window = webview.create_window(
                title=self.title,
                url=self.url,
                width=self.width,
                height=self.height,
                resizable=True,
                frameless=False,
                easy_drag=True,
                on_top=False,
                confirm_close=False,
                background_color="#0a0e1a",
            )

            # Set close handler
            self._window.events.closing += self._on_closing
            self._window.events.closed += self._on_closed

            logger.info("Window created")
            return self._window

        except ImportError:
            logger.error("pywebview not installed. Install: pip install pywebview")
            raise
        except Exception as e:
            logger.error(f"Failed to create window: {e}")
            raise

    def _on_closing(self):
        """Handle window closing - hide instead of close."""
        if self.on_close:
            self.on_close()
        return False  # Prevent actual close

    def _on_closed(self):
        """Handle window closed."""
        self._visible = False
        logger.info("Window closed")

    def show(self):
        """Show window."""
        if self._window:
            self._window.show()
            self._visible = True
            logger.info("Window shown")

    def hide(self):
        """Hide window."""
        if self._window:
            self._window.hide()
            self._visible = False
            logger.info("Window hidden")

    def toggle(self):
        """Toggle window visibility."""
        if self._visible:
            self.hide()
        else:
            self.show()

    def is_visible(self) -> bool:
        """Check if window is visible."""
        return self._visible

    def load_url(self, url: str):
        """Load new URL."""
        if self._window:
            self._window.load_url(url)

    def evaluate_js(self, script: str):
        """Evaluate JavaScript in window."""
        if self._window:
            self._window.evaluate_js(script)

    def run(self):
        """Run webview event loop (blocking)."""
        if self._webview and self._window:
            self._webview.start(debug=False)

    def destroy(self):
        """Destroy window."""
        if self._window:
            self._window.destroy()
            self._window = None
            self._visible = False


def run_window(
    url: str = "http://localhost:8080",
    title: str = "yuna",
    width: int = 1200,
    height: int = 800,
    on_close: Optional[Callable] = None,
):
    """
    Create and run window in main thread.

    Args:
        url: URL to load
        title: Window title
        width: Window width
        height: Window height
        on_close: Callback when user tries to close window
    """
    window = YunaWindow(url, title, width, height, on_close)
    window.create()
    window.show()
    window.run()
    return window


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def on_close():
        print("Window close requested")

    run_window(on_close=on_close)
