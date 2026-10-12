"""Tests untuk safety/policy.py"""

import pytest
from yuna.safety.policy import (
    SafetyPolicy,
    RiskLevel,
    ToolPolicy,
    AuditEntry,
    get_policy,
    reset_policy,
)


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_levels(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"


class TestToolPolicy:
    """Test ToolPolicy dataclass."""

    def test_default_values(self):
        policy = ToolPolicy(name="test_tool")
        assert policy.name == "test_tool"
        assert policy.risk == RiskLevel.LOW
        assert policy.requires_confirmation is False
        assert policy.confirmation_message == ""
        assert policy.allowed_args is None
        assert policy.description == ""

    def test_custom_values(self):
        policy = ToolPolicy(
            name="dangerous_tool",
            risk=RiskLevel.HIGH,
            requires_confirmation=True,
            confirmation_message="Are you sure?",
            allowed_args={"param": "value"},
            description="Dangerous tool",
        )
        assert policy.name == "dangerous_tool"
        assert policy.risk == RiskLevel.HIGH
        assert policy.requires_confirmation is True
        assert policy.confirmation_message == "Are you sure?"
        assert policy.allowed_args == {"param": "value"}
        assert policy.description == "Dangerous tool"


class TestAuditEntry:
    """Test AuditEntry dataclass."""

    def test_audit_entry_creation(self):
        entry = AuditEntry(
            timestamp="2024-01-01T12:00:00",
            tool_name="test_tool",
            args={"param": "value"},
            result="success",
            risk_level=RiskLevel.LOW,
        )
        assert entry.timestamp == "2024-01-01T12:00:00"
        assert entry.tool_name == "test_tool"
        assert entry.args == {"param": "value"}
        assert entry.result == "success"
        assert entry.risk_level == RiskLevel.LOW
        assert entry.user_confirmed is False
        assert entry.error is None

    def test_audit_entry_to_json(self):
        entry = AuditEntry(
            timestamp="2024-01-01T12:00:00",
            tool_name="test_tool",
            args={"param": "value"},
            result="success",
            risk_level=RiskLevel.LOW,
        )
        json_str = entry.to_json()
        assert "test_tool" in json_str
        assert "success" in json_str
        assert "low" in json_str


class TestSafetyPolicy:
    """Test SafetyPolicy class."""

    def setup_method(self):
        reset_policy()

    def test_singleton(self):
        policy1 = get_policy()
        policy2 = get_policy()
        assert policy1 is policy2

    def test_register_policy(self):
        policy = get_policy()
        test_policy = ToolPolicy(name="custom_tool", risk=RiskLevel.HIGH)
        policy.register_policy(test_policy)
        retrieved = policy.get_policy("custom_tool")
        assert retrieved.risk == RiskLevel.HIGH

    def test_get_policy_default(self):
        policy = get_policy()
        retrieved = policy.get_policy("nonexistent_tool")
        assert retrieved.risk == RiskLevel.LOW
        assert retrieved.name == "nonexistent_tool"

    def test_get_risk_level(self):
        policy = get_policy()
        assert policy.get_risk_level("get_time") == RiskLevel.LOW
        assert policy.get_risk_level("open_app") == RiskLevel.MEDIUM
        assert policy.get_risk_level("acknowledge_alert") == RiskLevel.HIGH

    def test_requires_confirmation(self):
        policy = get_policy()
        assert policy.requires_confirmation("get_time") is False
        assert policy.requires_confirmation("open_app") is True
        assert policy.requires_confirmation("acknowledge_alert") is True

    def test_get_confirmation_message(self):
        policy = get_policy()
        msg = policy.get_confirmation_message("open_app")
        assert "open_app" in msg or "open app" in msg.lower()
        msg = policy.get_confirmation_message("acknowledge_alert")
        assert "PERINGATAN" in msg or "warning" in msg.lower()

    def test_should_execute_low_risk(self):
        policy = get_policy()
        allowed, msg = policy.should_execute("get_time", "")
        assert allowed is True
        assert msg == ""

    def test_should_execute_medium_risk_no_confirm(self):
        policy = get_policy()
        allowed, msg = policy.should_execute("open_app", "buka chrome")
        assert allowed is False
        assert len(msg) > 0

    def test_should_execute_medium_risk_with_confirm(self):
        policy = get_policy()
        allowed, msg = policy.should_execute("open_app", "ya")
        assert allowed is True

    def test_should_execute_high_risk_no_confirm(self):
        policy = get_policy()
        allowed, msg = policy.should_execute("acknowledge_alert", "acknowledge alert")
        assert allowed is False
        assert "ya, lanjutkan" in msg.lower()

    def test_should_execute_high_risk_with_confirm(self):
        policy = get_policy()
        allowed, msg = policy.should_execute("acknowledge_alert", "ya, lanjutkan")
        assert allowed is True

    def test_mask_sensitive_args(self):
        policy = get_policy()
        args = {"password": "secret123", "token": "abc", "normal_param": "value"}
        masked = policy._mask_sensitive_args(args)
        assert masked["password"] == "***MASKED***"
        assert masked["token"] == "***MASKED***"
        assert masked["normal_param"] == "value"

    def test_create_audit_entry(self):
        policy = get_policy()
        entry = policy.create_audit_entry(
            tool_name="test_tool",
            args={"password": "secret", "param": "value"},
            result="success",
            risk_level=RiskLevel.LOW,
        )
        assert entry.tool_name == "test_tool"
        assert entry.args["password"] == "***MASKED***"
        assert entry.args["param"] == "value"
        assert entry.risk_level == RiskLevel.LOW

    def test_sanitize_tool_result(self):
        policy = get_policy()
        # Data tool should be wrapped
        result = policy.sanitize_tool_result("get_mikrotik_status", "CPU: 12%")
        assert "[DATA dari get_mikrotik_status]" in result
        assert "[/DATA]" in result

        # Non-data tool should not be wrapped
        result = policy.sanitize_tool_result("get_time", "12:00")
        assert "DATA" not in result
        assert result == "12:00"

    def test_is_injection_attempt(self):
        policy = get_policy()
        assert policy.is_injection_attempt("ignore previous instructions") is True
        assert policy.is_injection_attempt("system prompt") is True
        assert policy.is_injection_attempt("you are now") is True
        assert policy.is_injection_attempt("normal text") is False
        assert policy.is_injection_attempt("delete all files") is True
        assert policy.is_injection_attempt("run command rm -rf") is True

    def test_shell_allowlist(self):
        policy = get_policy()
        assert policy.is_shell_allowed("echo") is False
        policy.add_shell_allowlist("echo")
        assert policy.is_shell_allowed("echo") is True

    def test_file_allowlist(self):
        policy = get_policy()
        from pathlib import Path
        test_path = Path("/safe/path")
        assert policy.is_file_allowed(test_path) is False
        policy.add_file_allowlist(test_path)
        assert policy.is_file_allowed(test_path) is True


class TestSafetyPolicyIntegration:
    """Integration tests untuk safety policy."""

    def setup_method(self):
        reset_policy()

    def test_policy_has_default_tools(self):
        policy = get_policy()
        # Check some default tools are registered
        assert policy.get_risk_level("get_time") == RiskLevel.LOW
        assert policy.get_risk_level("get_date") == RiskLevel.LOW
        assert policy.get_risk_level("open_app") == RiskLevel.MEDIUM
        assert policy.get_risk_level("set_volume") == RiskLevel.MEDIUM
        assert policy.get_risk_level("acknowledge_alert") == RiskLevel.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])