"""Tests for sandbox tools."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPathJail:
    """Test path jail functionality."""

    def test_init(self):
        from yuna.sandbox.path_jail import get_path_jail, reset_path_jail
        reset_path_jail()
        jail = get_path_jail()
        assert jail.jail_root.exists()

    def test_is_allowed(self):
        from yuna.sandbox.path_jail import get_path_jail, reset_path_jail
        reset_path_jail()
        jail = get_path_jail()
        assert jail.is_allowed(jail.jail_root)
        assert not jail.is_allowed(Path("/tmp"))

    def test_resolve_safe(self):
        from yuna.sandbox.path_jail import get_path_jail, reset_path_jail
        reset_path_jail()
        jail = get_path_jail()
        safe = jail.resolve_safe("test.txt")
        assert safe.is_relative_to(jail.jail_root)

    def test_resolve_safe_escape_attempt(self):
        from yuna.sandbox.path_jail import get_path_jail, reset_path_jail
        reset_path_jail()
        jail = get_path_jail()
        with pytest.raises(ValueError):
            jail.resolve_safe("../outside")


class TestSandboxTools:
    """Test sandbox tool registration."""

    def _ensure_sandbox_loaded(self):
        """Import sandbox tools to ensure registration."""
        from yuna.sandbox import tools  # noqa: F401

    def test_journal_entry_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("journal_entry")
        assert tool is not None
        assert tool.risk == "low"

    def test_read_journal_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("read_journal")
        assert tool is not None

    def test_write_file_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("write_file")
        assert tool is not None
        assert tool.risk == "medium"

    def test_read_file_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("read_file")
        assert tool is not None

    def test_delete_file_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("delete_file")
        assert tool is not None
        assert tool.risk == "medium"

    def test_run_python_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("run_python")
        assert tool is not None
        assert tool.risk == "high"

    def test_run_shell_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("run_shell")
        assert tool is not None
        assert tool.risk == "high"

    def test_list_projects_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("list_projects")
        assert tool is not None

    def test_create_project_registered(self):
        self._ensure_sandbox_loaded()
        from yuna.tools.registry import get_registry
        reg = get_registry()
        tool = reg.get_tool("create_project")
        assert tool is not None
        assert tool.risk == "medium"


class TestSafetyPolicyIntegration:
    """Test that sandbox tools have correct risk levels."""

    def test_medium_risk_tools_include_sandbox(self):
        from yuna.safety.policy import get_policy
        policy = get_policy()
        for tool_name in ["write_file", "delete_file", "create_project"]:
            assert policy.get_risk_level(tool_name).value == "medium"

    def test_high_risk_tools_include_execution(self):
        from yuna.safety.policy import get_policy
        policy = get_policy()
        for tool_name in ["run_python", "run_shell"]:
            assert policy.get_risk_level(tool_name).value == "high"
