"""Reminder/alarm manager with TTS notifications."""

import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import sqlite3

from yuna.memory.db import get_db

logger = logging.getLogger(__name__)


class ReminderManager:
    """Manage reminders with background checking."""

    def __init__(self):
        self.db = get_db()
        self._checker_thread: Optional[threading.Thread] = None
        self._stop_checker = threading.Event()
        self._notification_callback: Optional[Callable[[str], None]] = None

    def add_reminder(self, reminder_time: datetime, message: str) -> int:
        """Add reminder."""
        created_at = datetime.now().isoformat()
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO reminders (reminder_time, message, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (reminder_time.isoformat(), message, created_at))
        self.db.commit()
        reminder_id = cursor.lastrowid
        logger.info(f"Reminder added: id={reminder_id}, time={reminder_time}, message={message}")
        return reminder_id

    def get_pending(self) -> List[Dict[str, Any]]:
        """Get all pending reminders."""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT * FROM reminders
            WHERE status = 'pending'
            ORDER BY reminder_time
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all reminders (including notified/cancelled)."""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT * FROM reminders
            ORDER BY reminder_time DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete reminder by id."""
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Reminder deleted: id={reminder_id}")
        return deleted

    def mark_notified(self, reminder_id: int):
        """Mark reminder as notified."""
        notified_at = datetime.now().isoformat()
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE reminders
            SET status = 'notified', notified_at = ?
            WHERE id = ?
        """, (notified_at, reminder_id))
        self.db.commit()
        logger.info(f"Reminder marked notified: id={reminder_id}")

    def mark_cancelled(self, reminder_id: int):
        """Mark reminder as cancelled."""
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE reminders
            SET status = 'cancelled'
            WHERE id = ?
        """, (reminder_id,))
        self.db.commit()
        logger.info(f"Reminder cancelled: id={reminder_id}")

    def check_due_reminders(self) -> List[Dict[str, Any]]:
        """Check reminders yang sudah waktunya."""
        now = datetime.now().isoformat()
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT * FROM reminders
            WHERE status = 'pending' AND reminder_time <= ?
            ORDER BY reminder_time
        """, (now,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def set_notification_callback(self, callback: Callable[[str], None]):
        """Set callback untuk trigger TTS saat reminder."""
        self._notification_callback = callback
        logger.info("Notification callback registered")

    def start_background_checker(self, interval_seconds: int = 10):
        """Start background thread untuk check reminders."""
        if self._checker_thread and self._checker_thread.is_alive():
            logger.warning("Background checker already running")
            return

        self._stop_checker.clear()
        self._checker_thread = threading.Thread(
            target=self._background_check_loop,
            args=(interval_seconds,),
            daemon=True,
            name="ReminderChecker"
        )
        self._checker_thread.start()
        logger.info(f"Background checker started (interval={interval_seconds}s)")

    def stop_background_checker(self):
        """Stop background checker."""
        if self._checker_thread and self._checker_thread.is_alive():
            self._stop_checker.set()
            self._checker_thread.join(timeout=5)
            logger.info("Background checker stopped")

    def _background_check_loop(self, interval_seconds: int):
        """Background loop untuk check reminders."""
        while not self._stop_checker.is_set():
            try:
                due_reminders = self.check_due_reminders()

                for reminder in due_reminders:
                    logger.info(f"Reminder due: {reminder['message']}")

                    # Trigger notification callback
                    if self._notification_callback:
                        try:
                            self._notification_callback(reminder['message'])
                        except Exception as e:
                            logger.error(f"Notification callback error: {e}")

                    # Mark as notified
                    self.mark_notified(reminder['id'])

            except Exception as e:
                logger.error(f"Background checker error: {e}", exc_info=True)

            # Sleep dengan check stop event
            self._stop_checker.wait(interval_seconds)

