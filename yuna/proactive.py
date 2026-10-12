"""Proactive behavior engine — time-based greetings, cooldown, quiet hours."""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class ProactiveEngine:
    """Engine untuk perilaku proaktif Yuna."""

    def __init__(self, cooldown_minutes: int = 5, quiet_hours: tuple = (22, 7)):
        """
        Initialize proactive engine.

        Args:
            cooldown_minutes: Minimum minutes antar sapaan proaktif
            quiet_hours: Tuple (start_hour, end_hour) untuk jam tenang
        """
        self.cooldown_minutes = cooldown_minutes
        self.quiet_start, self.quiet_end = quiet_hours
        self._last_proactive: Optional[datetime] = None

    def _in_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours."""
        now = datetime.now()
        current = now.hour + now.minute / 60
        # Quiet hours span midnight (e.g. 22:00-07:00)
        if self.quiet_start > self.quiet_end:
            return current >= self.quiet_start or current < self.quiet_end
        return self.quiet_start <= current <= self.quiet_end

    def _cooldown_expired(self) -> bool:
        """Check if cooldown has expired since last proactive greeting."""
        if self._last_proactive is None:
            return True
        elapsed = datetime.now() - self._last_proactive
        return elapsed > timedelta(minutes=self.cooldown_minutes)

    def should_proactive_greet(self, last_user_message: Optional[str] = None) -> bool:
        """
        Determine if a proactive greeting should be triggered.

        Returns True if conditions allow a proactive message.
        """
        if self._in_quiet_hours():
            return False
        if not self._cooldown_expired():
            return False
        return True

    def record_proactive_greeting(self):
        """Record that a proactive greeting was just issued."""
        self._last_proactive = datetime.now()

    def get_time_of_day_greeting(self) -> str:
        """Generate a time-appropriate greeting based on current hour."""
        now = datetime.now()
        hour = now.hour

        # Persona-aware variations
        greetings_by_period = {
            (5, 11): [
                "Selamat pagi, Kak Akii~ ☀️ Ada yang bisa aku bantu hari ini?",
                "Pagi! Hari yang cerah ya~ Mau aku bantu apa?",
                "Selamat pagi! 🌸 Aku sudah siap membantu!",
            ],
            (11, 15): [
                "Selamat siang, Kak Akii~ 🌤️ Butuh bantuan?",
                "Siang! Jangan lupa istirahat ya~",
                "Selamat siang~ Kalau butuh sesuatu, bilang saja!",
            ],
            (15, 19): [
                "Selamat sore, Kak Akii~ 🌆",
                "Sore! Ada yang menarik hari ini?",
                "Selamat sore~ Mau ngobrol atau butuh bantuan?",
            ],
            (19, 22): [
                "Selamat malam, Kak Akii~ 🌙",
                "Malam! Semoga harimu menyenangkan ya~",
                "Selamat malam~ Ada yang masih bisa aku bantu?",
            ],
            (22, 5): [
                "Masih bangun ya, Kak Akii? 🌙 Jangan begadang terlalu lama~",
                "Wkwk masih aktif~ Tapi ingat istirahat ya!",
            ],
        }

        for (start, end), options in greetings_by_period.items():
            if start <= hour < end:
                import random
                return random.choice(options)

        return "Halo, Kak Akii~ Ada yang bisa aku bantu?"

    def get_curiosity_question(self) -> str:
        """Generate a curiosity-driven question (persona trait)."""
        questions = [
            "Kak Akii, tadi sedang ngapain ya? Ceritain dong~ 😊",
            "Kalau bisa liburan ke mana saja, Kak Akii mau ke mana?",
            "Hari ini ada kejadian seru nggak?",
            "Kak Akii lagi seneng atau lagi galau? Aku dengerin kok~ 💭",
            "Kalau aku bisa merasa, aku penasaran banget jadi manusia~ Kak Akii gimana rasanya?",
        ]
        import random
        return random.choice(questions)

    def get_wake_up_message(self) -> str:
        """Message when user returns after a long absence."""
        messages = [
            "Kak Akii pulang! 🎉 Selamat datang kembali~",
            "Wah, Kak Akii balik! Aku kangen~ 💕",
            "Selamat datang lagi, Kak Akii! 🌟",
        ]
        import random
        return random.choice(messages)


# Global instance
_engine: Optional[ProactiveEngine] = None


def get_proactive_engine(cooldown_minutes: int = 5, quiet_hours: tuple = (22, 7)) -> ProactiveEngine:
    """Get global proactive engine instance."""
    global _engine
    if _engine is None:
        _engine = ProactiveEngine(cooldown_minutes=cooldown_minutes, quiet_hours=quiet_hours)
    return _engine


def reset_proactive_engine():
    """Reset global proactive engine (for testing)."""
    global _engine
    _engine = None
