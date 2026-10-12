"""Tests for memory module."""

import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from yuna.memory.db import init_db
from yuna.memory.conversation import ConversationHistory
from yuna.memory.facts import UserFacts
from yuna.memory.reminders import ReminderManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    # Create temp file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Create connection
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    yield conn, path

    # Cleanup
    conn.close()
    if os.path.exists(path):
        os.unlink(path)


def test_conversation_history_add_message(temp_db):
    """Test adding messages to conversation history."""
    conn, path = temp_db
    history = ConversationHistory()
    history.db = conn

    # Add messages
    history.add_message("user", "Hello")
    history.add_message("assistant", "Hi there!")

    # Check count
    assert history.get_count() == 2

    # Get recent
    messages = history.get_recent(limit=10)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"


def test_conversation_history_search(temp_db):
    """Test searching conversation history."""
    conn, path = temp_db
    history = ConversationHistory()
    history.db = conn

    # Add messages
    history.add_message("user", "What is the weather?")
    history.add_message("assistant", "It's sunny today!")
    history.add_message("user", "Open calculator")

    # Search
    results = history.search("weather")
    assert len(results) >= 1
    assert "weather" in results[0]["content"].lower()


def test_conversation_history_clear_old(temp_db):
    """Test clearing old messages."""
    conn, path = temp_db
    history = ConversationHistory()
    history.db = conn

    # Add many messages
    for i in range(50):
        history.add_message("user", f"Message {i}")

    # Clear old, keep 10
    deleted = history.clear_old(keep_recent=10)
    assert deleted == 40
    assert history.get_count() == 10


def test_user_facts_set_get(temp_db):
    """Test setting and getting user facts."""
    conn, path = temp_db
    facts = UserFacts()
    facts.db = conn

    # Set facts
    facts.set("name", "Akii")
    facts.set("favorite_color", "blue")

    # Get facts
    assert facts.get("name") == "Akii"
    assert facts.get("favorite_color") == "blue"
    assert facts.get("nonexistent") is None


def test_user_facts_update(temp_db):
    """Test updating existing fact."""
    conn, path = temp_db
    facts = UserFacts()
    facts.db = conn

    # Set and update
    facts.set("status", "happy")
    facts.set("status", "excited")

    # Should be updated
    assert facts.get("status") == "excited"


def test_user_facts_delete(temp_db):
    """Test deleting fact."""
    conn, path = temp_db
    facts = UserFacts()
    facts.db = conn

    # Set and delete
    facts.set("temp", "value")
    assert facts.get("temp") == "value"

    deleted = facts.delete("temp")
    assert deleted is True
    assert facts.get("temp") is None


def test_user_facts_get_all(temp_db):
    """Test getting all facts."""
    conn, path = temp_db
    facts = UserFacts()
    facts.db = conn

    # Set multiple facts
    facts.set("name", "Akii")
    facts.set("age", "25")
    facts.set("city", "Jakarta")

    # Get all
    all_facts = facts.get_all()
    assert len(all_facts) == 3
    assert all_facts["name"] == "Akii"
    assert all_facts["city"] == "Jakarta"


def test_reminder_manager_add(temp_db):
    """Test adding reminder."""
    conn, path = temp_db
    manager = ReminderManager()
    manager.db = conn

    # Add reminder
    reminder_time = datetime.now() + timedelta(minutes=30)
    reminder_id = manager.add_reminder(reminder_time, "Test reminder")

    assert reminder_id > 0

    # Check pending
    pending = manager.get_pending()
    assert len(pending) == 1
    assert pending[0]["message"] == "Test reminder"


def test_reminder_manager_mark_notified(temp_db):
    """Test marking reminder as notified."""
    conn, path = temp_db
    manager = ReminderManager()
    manager.db = conn

    # Add and mark
    reminder_time = datetime.now() + timedelta(minutes=30)
    reminder_id = manager.add_reminder(reminder_time, "Test")

    manager.mark_notified(reminder_id)

    # Should not be in pending
    pending = manager.get_pending()
    assert len(pending) == 0


def test_reminder_manager_check_due(temp_db):
    """Test checking due reminders."""
    conn, path = temp_db
    manager = ReminderManager()
    manager.db = conn

    # Add past reminder (should be due)
    past_time = datetime.now() - timedelta(minutes=5)
    manager.add_reminder(past_time, "Past reminder")

    # Add future reminder (not due yet)
    future_time = datetime.now() + timedelta(minutes=30)
    manager.add_reminder(future_time, "Future reminder")

    # Check due
    due = manager.check_due_reminders()
    assert len(due) == 1
    assert due[0]["message"] == "Past reminder"


def test_reminder_manager_delete(temp_db):
    """Test deleting reminder."""
    conn, path = temp_db
    manager = ReminderManager()
    manager.db = conn

    # Add and delete
    reminder_time = datetime.now() + timedelta(minutes=30)
    reminder_id = manager.add_reminder(reminder_time, "Test")

    deleted = manager.delete_reminder(reminder_id)
    assert deleted is True

    # Should not be in pending
    pending = manager.get_pending()
    assert len(pending) == 0
