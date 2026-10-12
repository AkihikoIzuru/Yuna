"""Memory tools - conversation history, facts, reminders."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from yuna.tools.registry import tool
from yuna.memory import ConversationHistory, UserFacts, ReminderManager

logger = logging.getLogger(__name__)

# Global instances
_conversation_history: Optional[ConversationHistory] = None
_user_facts: Optional[UserFacts] = None
_reminder_manager: Optional[ReminderManager] = None


def get_conversation_history() -> ConversationHistory:
    """Get conversation history instance."""
    global _conversation_history
    if _conversation_history is None:
        _conversation_history = ConversationHistory()
    return _conversation_history


def get_user_facts() -> UserFacts:
    """Get user facts instance."""
    global _user_facts
    if _user_facts is None:
        _user_facts = UserFacts()
    return _user_facts


def get_reminder_manager() -> ReminderManager:
    """Get reminder manager instance."""
    global _reminder_manager
    if _reminder_manager is None:
        _reminder_manager = ReminderManager()
    return _reminder_manager


@tool(risk="low")
def remember_fact(key: str, value: str) -> str:
    """Simpan fakta tentang user (nama, hobi, preferensi, dll)."""
    facts = get_user_facts()
    facts.set(key, value)
    return f"Fakta tersimpan: {key} = {value}"


@tool(risk="low")
def recall_fact(key: str) -> str:
    """Ambil fakta tentang user by key."""
    facts = get_user_facts()
    value = facts.get(key)
    if value:
        return f"{key}: {value}"
    return f"Fakta '{key}' tidak ditemukan"


@tool(risk="low")
def forget_fact(key: str) -> str:
    """Hapus fakta tentang user."""
    facts = get_user_facts()
    deleted = facts.delete(key)
    if deleted:
        return f"Fakta '{key}' dihapus"
    return f"Fakta '{key}' tidak ditemukan"


@tool(risk="low")
def list_facts() -> str:
    """List semua fakta tentang user."""
    facts = get_user_facts()
    all_facts = facts.get_all()

    if not all_facts:
        return "Belum ada fakta tersimpan"

    lines = ["Fakta tersimpan:"]
    for key, value in all_facts.items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)


@tool(risk="low")
def search_conversation(query: str, limit: int = 10) -> str:
    """Cari di riwayat percakapan."""
    history = get_conversation_history()
    messages = history.search(query, limit=limit)

    if not messages:
        return f"Tidak ada hasil untuk '{query}'"

    lines = [f"Hasil pencarian '{query}' ({len(messages)} pesan):"]
    for msg in messages:
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%Y-%m-%d %H:%M")
        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        lines.append(f"[{timestamp}] {msg['role']}: {content}")

    return "\n".join(lines)


@tool(risk="low")
def add_reminder(message: str, minutes_from_now: int) -> str:
    """Buat reminder/alarm. Contoh: add_reminder('minum obat', 30) = reminder 30 menit dari sekarang."""
    reminder_manager = get_reminder_manager()

    # Calculate reminder time
    reminder_time = datetime.now() + timedelta(minutes=minutes_from_now)

    # Add reminder
    reminder_id = reminder_manager.add_reminder(reminder_time, message)

    time_str = reminder_time.strftime("%H:%M")
    return f"Reminder diset untuk {time_str} ({minutes_from_now} menit dari sekarang): {message}"


@tool(risk="low")
def list_reminders() -> str:
    """List semua reminder yang aktif."""
    reminder_manager = get_reminder_manager()
    reminders = reminder_manager.get_pending()

    if not reminders:
        return "Tidak ada reminder aktif"

    lines = [f"Reminder aktif ({len(reminders)}):"]
    for r in reminders:
        reminder_time = datetime.fromisoformat(r['reminder_time'])
        time_str = reminder_time.strftime("%Y-%m-%d %H:%M")
        lines.append(f"- [{r['id']}] {time_str}: {r['message']}")

    return "\n".join(lines)


@tool(risk="low")
def delete_reminder(reminder_id: int) -> str:
    """Hapus reminder by ID."""
    reminder_manager = get_reminder_manager()
    deleted = reminder_manager.delete_reminder(reminder_id)

    if deleted:
        return f"Reminder #{reminder_id} dihapus"
    return f"Reminder #{reminder_id} tidak ditemukan"

