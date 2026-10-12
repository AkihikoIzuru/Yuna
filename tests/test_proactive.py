"""Tests for ProactiveEngine."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from yuna.proactive import ProactiveEngine, get_proactive_engine, reset_proactive_engine


class TestProactiveEngine:
    """Test proactive engine."""

    def test_init(self):
        engine = ProactiveEngine(cooldown_minutes=10, quiet_hours=(22, 6))
        assert engine.cooldown_minutes == 10
        assert engine.quiet_start == 22
        assert engine.quiet_end == 6
        assert engine._last_proactive is None

    def test_in_quiet_hours_night(self):
        """22:00-06:00 should be quiet hours."""
        engine = ProactiveEngine(quiet_hours=(22, 6))
        with patch("yuna.proactive.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 23, 0)
            assert engine._in_quiet_hours() is True
            mock_dt.now.return_value = datetime(2024, 1, 1, 2, 0)
            assert engine._in_quiet_hours() is True
            mock_dt.now.return_value = datetime(2024, 1, 1, 5, 59)
            assert engine._in_quiet_hours() is True

    def test_in_quiet_hours_day(self):
        """Daytime should NOT be quiet hours."""
        engine = ProactiveEngine(quiet_hours=(22, 6))
        with patch("yuna.proactive.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 10, 0)
            assert engine._in_quiet_hours() is False
            mock_dt.now.return_value = datetime(2024, 1, 1, 14, 0)
            assert engine._in_quiet_hours() is False
            mock_dt.now.return_value = datetime(2024, 1, 1, 20, 0)
            assert engine._in_quiet_hours() is False

    def test_in_quiet_hours_spanning_midnight(self):
        """Test quiet hours that span midnight (22-7)."""
        engine = ProactiveEngine(quiet_hours=(22, 7))
        with patch("yuna.proactive.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 22, 30)
            assert engine._in_quiet_hours() is True
            mock_dt.now.return_value = datetime(2024, 1, 1, 3, 0)
            assert engine._in_quiet_hours() is True
            # 7:00 is exactly at end boundary, should NOT be in quiet hours
            mock_dt.now.return_value = datetime(2024, 1, 1, 7, 0)
            assert engine._in_quiet_hours() is False
            # 6:59 IS in quiet hours
            mock_dt.now.return_value = datetime(2024, 1, 1, 6, 59)
            assert engine._in_quiet_hours() is True

    def test_cooldown_expired_none(self):
        engine = ProactiveEngine(cooldown_minutes=5)
        assert engine._cooldown_expired() is True

    def test_cooldown_expired_recent(self):
        engine = ProactiveEngine(cooldown_minutes=5)
        engine._last_proactive = datetime.now()
        assert engine._cooldown_expired() is False

    def test_cooldown_expired_old(self):
        engine = ProactiveEngine(cooldown_minutes=5)
        engine._last_proactive = datetime.now() - timedelta(minutes=10)
        assert engine._cooldown_expired() is True

    def test_should_proactive_greet_quiet_hours(self):
        engine = ProactiveEngine(quiet_hours=(22, 6))
        with patch.object(engine, "_in_quiet_hours", return_value=True):
            assert engine.should_proactive_greet() is False

    def test_should_proactive_greet_cooldown_active(self):
        engine = ProactiveEngine(cooldown_minutes=5)
        engine._last_proactive = datetime.now()
        with patch.object(engine, "_in_quiet_hours", return_value=False):
            assert engine.should_proactive_greet() is False

    def test_should_proactive_greet_ok(self):
        engine = ProactiveEngine(cooldown_minutes=5)
        engine._last_proactive = datetime.now() - timedelta(minutes=10)
        with patch.object(engine, "_in_quiet_hours", return_value=False):
            assert engine.should_proactive_greet() is True

    def test_record_proactive_greeting(self):
        engine = ProactiveEngine()
        before = datetime.now()
        engine.record_proactive_greeting()
        assert engine._last_proactive is not None
        assert engine._last_proactive >= before

    def test_get_time_of_day_greeting_morning(self):
        engine = ProactiveEngine()
        with patch("yuna.proactive.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 8, 0)
            greeting = engine.get_time_of_day_greeting()
            assert "pagi" in greeting.lower() or "Pagi" in greeting

    def test_get_time_of_day_greeting_evening(self):
        engine = ProactiveEngine()
        with patch("yuna.proactive.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 20, 0)
            greeting = engine.get_time_of_day_greeting()
            assert "malam" in greeting.lower() or "Malam" in greeting

    def test_get_time_of_day_greeting_default(self):
        engine = ProactiveEngine()
        # Patch datetime to return an hour outside all defined ranges (none exist since ranges cover 0-24)
        # All hours 0-23 are covered by the ranges, so default is unreachable
        # Just verify it returns a valid greeting
        greeting = engine.get_time_of_day_greeting()
        assert isinstance(greeting, str)
        assert len(greeting) > 0

    def test_get_curiosity_question(self):
        engine = ProactiveEngine()
        question = engine.get_curiosity_question()
        assert isinstance(question, str)
        assert len(question) > 0

    def test_get_wake_up_message(self):
        engine = ProactiveEngine()
        message = engine.get_wake_up_message()
        assert isinstance(message, str)
        assert len(message) > 0

    def test_singleton(self):
        reset_proactive_engine()
        e1 = get_proactive_engine(cooldown_minutes=10)
        e2 = get_proactive_engine(cooldown_minutes=10)
        assert e1 is e2
        reset_proactive_engine()
