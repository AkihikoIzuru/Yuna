"""Tests untuk tool registry."""

import pytest
from yuna.tools.registry import ToolRegistry, tool, get_registry


def test_basic_tool_registration():
    """Test registrasi tool dasar."""
    registry = ToolRegistry()

    @tool(risk="low")
    def test_func(name: str, age: int = 25) -> str:
        """Test function."""
        return f"{name} is {age}"

    # Re-register ke registry test
    registry.register(test_func, risk="low")

    registered = registry.get_tool("test_func")
    assert registered is not None
    assert registered.name == "test_func"
    assert registered.description == "Test function."
    assert registered.risk == "low"


def test_tool_parameters_schema():
    """Test auto-generate JSON schema dari type hints."""
    registry = ToolRegistry()

    @tool(risk="low")
    def sample_tool(text: str, count: int, flag: bool = False) -> str:
        """Sample tool."""
        return f"{text} x {count}"

    registry.register(sample_tool)
    registered = registry.get_tool("sample_tool")

    params = registered.parameters
    assert params["type"] == "object"
    assert "text" in params["properties"]
    assert "count" in params["properties"]
    assert "flag" in params["properties"]

    # Required params (no default)
    assert "text" in params["required"]
    assert "count" in params["required"]
    assert "flag" not in params["required"]  # has default

    # Types
    assert params["properties"]["text"]["type"] == "string"
    assert params["properties"]["count"]["type"] == "integer"
    assert params["properties"]["flag"]["type"] == "boolean"


def test_openai_tools_format():
    """Test format OpenAI function calling."""
    registry = ToolRegistry()

    @tool(risk="low")
    def get_weather(city: str) -> str:
        """Get weather for a city."""
        return f"Weather in {city}"

    registry.register(get_weather)
    tools = registry.get_openai_tools()

    assert len(tools) >= 1
    tool_def = next(t for t in tools if t["function"]["name"] == "get_weather")

    assert tool_def["type"] == "function"
    assert tool_def["function"]["name"] == "get_weather"
    assert tool_def["function"]["description"] == "Get weather for a city."
    assert "city" in tool_def["function"]["parameters"]["properties"]


def test_tool_execution():
    """Test eksekusi tool."""
    registry = ToolRegistry()

    @tool(risk="low")
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    registry.register(add_numbers)

    result = registry.call("add_numbers", {"a": 5, "b": 3})
    assert result == 8


def test_tool_execution_error():
    """Test error handling saat eksekusi tool."""
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="tidak ditemukan"):
        registry.call("nonexistent_tool", {})


def test_tool_execution_ignores_extra_kwargs():
    """Test bahwa tool call mengabaikan argumen tambahan yang tidak di signature (seperti 'reason')."""
    registry = ToolRegistry()

    @tool(risk="low")
    def get_date() -> str:
        """Get current date."""
        return "2026-10-12"

    registry.register(get_date)

    # Simulate model adding extra 'reason' arg
    result = registry.call("get_date", {"reason": "user asked for date"})
    assert result == "2026-10-12"


def test_openai_tools_additional_properties_false():
    """Test bahwa JSON schema memiliki additionalProperties: false."""
    registry = ToolRegistry()

    @tool(risk="low")
    def sample_tool(text: str) -> str:
        """Sample tool."""
        return text

    registry.register(sample_tool)
    tools = registry.get_openai_tools()
    tool_def = next(t for t in tools if t["function"]["name"] == "sample_tool")

    assert tool_def["function"]["parameters"].get("additionalProperties") is False