"""Conversation history management."""

import logging
from datetime import datetime
from typing import List, Dict, Any
import sqlite3

from yuna.memory.db import get_db

logger = logging.getLogger(__name__)


class ConversationHistory:
    """Manage conversation history."""

    def __init__(self):
        self.db = get_db()

    def add_message(self, role: str, content: str, summary: str = None):
        """Simpan message ke database."""
        timestamp = datetime.now().isoformat()
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO conversations (timestamp, role, content, summary) VALUES (?, ?, ?, ?)",
            (timestamp, role, content, summary)
        )
        self.db.commit()
        logger.debug(f"Saved message: role={role}, length={len(content)}")

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages."""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()

        # Convert Row to dict dan reverse (newest last)
        messages = []
        for row in reversed(rows):
            messages.append({
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "summary": row["summary"],
            })

        return messages

    def get_count(self) -> int:
        """Get total message count."""
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM conversations")
        return cursor.fetchone()["count"]

    def clear_old(self, keep_recent: int = 100):
        """Hapus message lama, keep N terakhir."""
        cursor = self.db.cursor()
        cursor.execute("""
            DELETE FROM conversations
            WHERE id NOT IN (
                SELECT id FROM conversations
                ORDER BY timestamp DESC
                LIMIT ?
            )
        """, (keep_recent,))
        self.db.commit()
        deleted = cursor.rowcount
        logger.info(f"Cleared {deleted} old messages")
        return deleted

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search messages by content."""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT * FROM conversations
            WHERE content LIKE ? OR summary LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))

        rows = cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
                "summary": row["summary"],
            })

        return messages

