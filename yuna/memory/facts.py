"""User facts storage (key-value)."""

import logging
from datetime import datetime
from typing import Optional, Dict
import sqlite3

from yuna.memory.db import get_db

logger = logging.getLogger(__name__)


class UserFacts:
    """Manage facts about user (key-value store)."""

    def __init__(self):
        self.db = get_db()

    def set(self, key: str, value: str):
        """Set atau update fact."""
        timestamp = datetime.now().isoformat()
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO facts (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
        """, (key, value, timestamp))
        self.db.commit()
        logger.info(f"Fact saved: {key} = {value}")

    def get(self, key: str) -> Optional[str]:
        """Get fact by key."""
        cursor = self.db.cursor()
        cursor.execute("SELECT value FROM facts WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def delete(self, key: str) -> bool:
        """Delete fact."""
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM facts WHERE key = ?", (key,))
        self.db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Fact deleted: {key}")
        return deleted

    def get_all(self) -> Dict[str, str]:
        """Get all facts."""
        cursor = self.db.cursor()
        cursor.execute("SELECT key, value FROM facts ORDER BY key")
        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

    def search(self, query: str) -> Dict[str, str]:
        """Search facts by key or value."""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT key, value FROM facts
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY key
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        return {row["key"]: row["value"] for row in rows}

