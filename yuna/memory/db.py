"""Database connection and schema initialization."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Database path - simpan di folder proyek
DB_PATH = Path(__file__).parent.parent.parent / "yuna.db"

_db_connection: Optional[sqlite3.Connection] = None


def get_db() -> sqlite3.Connection:
    """Get atau buat koneksi database."""
    global _db_connection

    if _db_connection is None:
        logger.info(f"Opening database: {DB_PATH}")
        _db_connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _db_connection.row_factory = sqlite3.Row  # Akses kolom by name
        init_db(_db_connection)

    return _db_connection


def init_db(conn: sqlite3.Connection):
    """Initialize database schema."""
    cursor = conn.cursor()

    # Table: conversations - riwayat percakapan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT
        )
    """)

    # Table: facts - fakta tentang user (key-value)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Table: reminders - reminder/alarm
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder_time TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            notified_at TEXT
        )
    """)

    # Index untuk query cepat
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
        ON conversations(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_time_status
        ON reminders(reminder_time, status)
    """)

    conn.commit()
    logger.info("Database initialized")


def close_db():
    """Close database connection."""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None
        logger.info("Database closed")

