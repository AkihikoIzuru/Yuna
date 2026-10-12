"""Tests untuk logging setup."""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_setup_logging():
    """Test setup_logging creates handlers."""
    import logging
    from yuna.app.logging_setup import setup_logging
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('yuna.app.logging_setup.get_log_dir', return_value=Path(tmpdir)):
            logger = setup_logging(level="DEBUG")
            assert len(logger.handlers) >= 2  # console + file
            # Close handlers to allow cleanup
            for h in logger.handlers[:]:
                h.close()
                logger.removeHandler(h)


def test_mask_log_message():
    """Test masking sensitive values in log messages."""
    from yuna.app.logging_setup import mask_log_message

    # Test API key masking
    msg = "API_KEY=sk-1234567890abcdef"
    masked = mask_log_message(msg)
    assert "****" in masked  # masked contains ****
    assert "sk-1234567890abcdef" not in masked

    # Test password masking
    msg = "password=mysecretpassword"
    masked = mask_log_message(msg)
    assert "****" in masked

    # Test non-sensitive message
    msg = "Normal log message"
    assert mask_log_message(msg) == msg


def test_check_data_directory():
    """Test data directory check."""
    from yuna.app.logging_setup import check_data_directory
    # Should work on normal system
    result = check_data_directory()
    assert result is True


def test_get_health_status():
    """Test health status reporting."""
    from yuna.app.logging_setup import get_health_status
    status = get_health_status()
    assert isinstance(status, dict)
    assert "system" in status
    assert "python" in status
    # 9router might fail if not running
    assert "9router" in status


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
