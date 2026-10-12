"""Database connection and schema initialization."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from yuna.config import get_config

logger = logging.getLogger(__name__)

_db_connection: Optional[sqlite3.Connection] = None


def _get_db_path() -> Path:
    """Get database path from config."""
    config = get_config()
    if config.data_dir:
        data_dir = Path(config.data_dir)
    else:
        data_dir = Path(__file__).parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "yuna.db"


def get_db() -> sqlite3.Connection:
    """Get atau buat koneksi database."""
    global _db_connection

    if _db_connection is None:
        db_path = _get_db_path()
        logger.info(f"Opening database: {db_path}")
        _db_connection = sqlite3.connect(str(db_path), check_same_thread=False)
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

