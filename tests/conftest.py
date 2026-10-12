"""Shared fixtures for all tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def _setup_test_env():
    """Set minimal env vars before any tests run."""
    os.environ.setdefault("YUNA_BASE_URL", "http://localhost:20128/v1")
    os.environ.setdefault("YUNA_MODEL", "yuna")
    os.environ.setdefault("YUNA_FAST_MODEL", "yuna")
    os.environ.setdefault("ROUTER_API_KEY", "test-key")
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
    os.environ.setdefault("LOG_DIR", tempfile.mkdtemp())


@pytest.fixture
def mock_config():
    """Mock get_config() to avoid loading .env."""
    from yuna.config import reset_config
    reset_config()
    cfg = MagicMock()
    cfg.base_url = "http://localhost:20128/v1"
    cfg.model = "yuna"
    cfg.fast_model = "yuna"
    cfg.api_key = "test-key"
    cfg.wake_word = "hey yuna"
    cfg.wake_backend = "auto"
    cfg.wake_phrases = "yuna,yu na,yuuna,juna"
    cfg.tts_voice = "id-ID-GadisNeural"
    cfg.tts_rate = "+3%"
    cfg.tts_pitch = "+3Hz"
    cfg.ui_host = "127.0.0.1"
    cfg.ui_port = 8080
    cfg.data_dir = tempfile.mkdtemp()
    cfg.log_dir = tempfile.mkdtemp()
    with patch("yuna.config._config", cfg):
        yield cfg


@pytest.fixture
def temp_data_dir():
    """Temporary directory for sandbox/file ops testing."""
    d = tempfile.mkdtemp(prefix="yuna-test-")
    yield d
    # Cleanup handled by OS


@pytest.fixture(autouse=True)
def _reset_singletons(mock_config):
    """Reset all singletons after each test."""
    from yuna.safety.policy import reset_policy
    from yuna.sandbox.path_jail import reset_path_jail
    from yuna.brain.agent import reset_agent
    from yuna.config import reset_config
    from yuna.voice.wake import reset_wake_detector
    from yuna.proactive import reset_proactive_engine

    reset_policy()
    reset_path_jail()
    reset_agent()
    reset_config()
    reset_wake_detector()
    reset_proactive_engine()
