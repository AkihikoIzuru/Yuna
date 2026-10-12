"""Windows Toast notifications."""

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manage Windows toast notifications."""

    def __init__(self, app_id: str = "yuna"):
        self.app_id = app_id
        self._toaster = None
        self._enabled = True

    def initialize(self) -> bool:
        """Initialize Windows toast notifier."""
        try:
            from windows_toasts import Toast, InteractableToast, WindowsToaster
            self._toaster = WindowsToaster(self.app_id)
            logger.info("Windows toast notifications initialized")
            return True
        except ImportError:
            logger.warning("windows-toasts not installed, using fallback")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize toast: {e}")
            return False

    def show(
        self,
        title: str,
        message: str,
        duration: str = "short",
        on_click: Optional[callable] = None,
    ):
        """Show toast notification."""
        if not self._enabled:
            return

        if self._toaster is None:
            # Fallback: print to console
            print(f"ðŸ”” {title}: {message}")
            if on_click:
                on_click()
            return

        try:
            from windows_toasts import Toast
            toast = Toast()
            toast.text_fields = [title, message]
            toast.duration = duration

            if on_click:
                toast.on_activated = lambda _: on_click()

            self._toaster.show_toast(toast)
        except Exception as e:
            logger.error(f"Failed to show toast: {e}")
            print(f"ðŸ”” {title}: {message}")

    def show_reminder(self, message: str):
        """Show reminder notification."""
        self.show("â° Reminder", message, duration="long")

    def show_alert(self, title: str, message: str, level: str = "info"):
        """Show alert notification."""
        icons = {
            "info": "â„¹ï¸",
            "warning": "âš ï¸",
            "critical": "ðŸ”´",
        }
        icon = icons.get(level, "â„¹ï¸")
        self.show(f"{icon} {title}", message, duration="long")

    def show_network_status(self, status: str, detail: str = ""):
        """Show network status change."""
        icons = {
            "connected": "âœ…",
            "disconnected": "âŒ",
            "warning": "âš ï¸",
        }
        icon = icons.get(status, "â„¹ï¸")
        self.show(f"{icon} Jaringan {status}", detail)

    def enable(self):
        """Enable notifications."""
        self._enabled = True

    def disable(self):
        """Disable notifications."""
        self._enabled = False


# Fallback notification for when windows-toasts not available
class FallbackNotifier:
    """Simple fallback notifier using console output."""

    def __init__(self):
        self._enabled = True

    def show(self, title: str, message: str, **kwargs):
        if self._enabled:
            print(f"ðŸ”” {title}: {message}")

    def show_reminder(self, message: str):
        print(f"â° Reminder: {message}")

    def show_alert(self, title: str, message: str, level: str = "info"):
        icons = {"info": "â„¹ï¸", "warning": "âš ï¸", "critical": "ðŸ”´"}
        icon = icons.get(level, "â„¹ï¸")
        print(f"{icon} {title}: {message}")

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False


# Global notifier
_notifier: Optional[NotificationManager] = None


def get_notifier() -> NotificationManager:
    """Get global notifier (with fallback)."""
    global _notifier
    if _notifier is None:
        _notifier = NotificationManager()
        if not _notifier.initialize():
            # Use fallback
            _notifier = FallbackNotifier()
    return _notifier


def notify(title: str, message: str, **kwargs):
    """Quick notification."""
    get_notifier().show(title, message, **kwargs)


def notify_reminder(message: str):
    """Quick reminder notification."""
    get_notifier().show_reminder(message)


def notify_alert(title: str, message: str, level: str = "info"):
    """Quick alert notification."""
    get_notifier().show_alert(title, message, level)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    notifier = get_notifier()
    notifier.show("Test", "Hello from Yuna!")
    notifier.show_reminder("Test reminder")
    notifier.show_alert("Test Alert", "This is a test alert", "warning")
