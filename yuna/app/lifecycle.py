"""Lifecycle management untuk Yuna app (single instance, startup/shutdown)."""

import atexit
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SingleInstance:
    """Ensure only one instance of Yuna runs."""

    def __init__(self, name: str = "yuna"):
        self.name = name
        self._lock_file: Optional[Path] = None
        self._lock_fd = None
        self._acquired = False

    def acquire(self) -> bool:
        """
        Try to acquire single instance lock.

        Returns:
            True if acquired (this is the first instance), False if another instance exists
        """
        lock_dir = Path(tempfile.gettempdir()) / "yuna"
        lock_dir.mkdir(exist_ok=True)
        self._lock_file = lock_dir / f"{self.name}.lock"

        try:
            # Try to create lock file exclusively
            self._lock_fd = os.open(self._lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            # Write PID
            os.write(self._lock_fd, str(os.getpid()).encode())
            os.fsync(self._lock_fd)
            self._acquired = True
            logger.info(f"Single instance lock acquired: {self._lock_file}")
            return True
        except FileExistsError:
            # Lock file exists, check if process is still alive
            try:
                with open(self._lock_file, "r") as f:
                    pid_str = f.read().strip()
                    if pid_str:
                        pid = int(pid_str)
                        if self._is_process_alive(pid):
                            logger.info(f"Another instance running (PID: {pid})")
                            return False
                        else:
                            logger.info(f"Stale lock file (PID {pid} dead), taking over")
                            # Remove stale lock and try again
                            os.remove(self._lock_file)
                            return self.acquire()
            except (ValueError, OSError):
                pass
            return False
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False

    def _is_process_alive(self, pid: int) -> bool:
        """Check if process is alive."""
        try:
            # Windows: use OpenProcess
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            # Fallback: try os.kill with signal 0 (Unix-like)
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def release(self):
        """Release the lock."""
        if self._acquired and self._lock_fd is not None:
            try:
                os.close(self._lock_fd)
                if self._lock_file and self._lock_file.exists():
                    self._lock_file.unlink()
                logger.info("Single instance lock released")
            except Exception as e:
                logger.error(f"Failed to release lock: {e}")
            finally:
                self._acquired = False
                self._lock_fd = None


class LifecycleManager:
    """Manage application lifecycle: startup, shutdown, health checks."""

    def __init__(self):
        self._running = False
        self._shutdown_event = threading.Event()
        self._startup_callbacks = []
        self._shutdown_callbacks = []
        self._health_check_callbacks = []
        self._single_instance = SingleInstance("yuna")
        self._background_threads = []

    def add_startup_callback(self, callback: Callable):
        """Add callback to run on startup."""
        self._startup_callbacks.append(callback)

    def add_shutdown_callback(self, callback: Callable):
        """Add callback to run on shutdown."""
        self._shutdown_callbacks.append(callback)

    def add_health_check(self, callback: Callable):
        """Add health check callback."""
        self._health_check_callbacks.append(callback)

    def start(self, force: bool = False) -> bool:
        """
        Start lifecycle.

        Args:
            force: Force start even if another instance exists

        Returns:
            True if started successfully, False if another instance running
        """
        if self._running:
            logger.warning("Already running")
            return True

        # Check single instance
        if not force and not self._single_instance.acquire():
            return False

        self._running = True
        logger.info("Starting lifecycle...")

        # Register atexit handler
        atexit.register(self.shutdown)

        # Run startup callbacks
        for cb in self._startup_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Startup callback failed: {e}")

        return True

    def shutdown(self, timeout: float = 10.0):
        """Shutdown gracefully."""
        if not self._running:
            return

        logger.info("Shutting down...")
        self._running = False
        self._shutdown_event.set()

        # Run shutdown callbacks
        for cb in self._shutdown_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Shutdown callback failed: {e}")

        # Wait for background threads
        for thread in self._background_threads:
            if thread.is_alive():
                thread.join(timeout=timeout / max(len(self._background_threads), 1))

        # Release single instance lock
        self._single_instance.release()

        logger.info("Shutdown complete")

    def run_background(self, target: Callable, name: str = "background") -> threading.Thread:
        """Run a function in background thread."""
        thread = threading.Thread(target=target, name=f"yuna-{name}", daemon=True)
        thread.start()
        self._background_threads.append(thread)
        return thread

    def wait_for_shutdown(self):
        """Block until shutdown is requested."""
        self._shutdown_event.wait()

    def is_running(self) -> bool:
        """Check if running."""
        return self._running

    def run_health_checks(self) -> dict:
        """Run all health checks."""
        results = {}
        for cb in self._health_check_callbacks:
            try:
                result = cb()
                results[cb.__name__] = {"healthy": True, "detail": result}
            except Exception as e:
                results[cb.__name__] = {"healthy": False, "error": str(e)}
        return results


# Global lifecycle manager
_lifecycle: Optional[LifecycleManager] = None


def get_lifecycle() -> LifecycleManager:
    """Get global lifecycle manager."""
    global _lifecycle
    if _lifecycle is None:
        _lifecycle = LifecycleManager()
    return _lifecycle


def reset_lifecycle():
    """Reset lifecycle (for testing)."""
    global _lifecycle
    if _lifecycle:
        _lifecycle.shutdown()
    _lifecycle = None
