"""Tests for Agent class."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yuna.brain.agent import Agent, get_agent, reset_agent
from yuna.tools.registry import get_registry


class TestAgent:
    """Test the main Agent class."""

    def setup_method(self):
        reset_agent()

    def teardown_method(self):
        reset_agent()

    def test_build_messages(self):
        agent = Agent()
        history = [
            {"role": "user", "content": "Halo"},
            {"role": "assistant", "content": "Halo juga!"},
        ]
        messages = agent._build_messages("Apa kabar?", history)

        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert "yuna" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Halo"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Halo juga!"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Apa kabar?"

    def test_build_messages_empty_history(self):
        agent = Agent()
        messages = agent._build_messages("Test")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Test"

    def test_normalize_tool_call_format1(self):
        agent = Agent()
        parsed = {"tool": "get_time", "args": {}}
        result = agent._normalize_tool_call(parsed)
        assert result == {"tool": "get_time", "args": {}}

    def test_normalize_tool_call_format2(self):
        agent = Agent()
        parsed = {"tool": "get_time", "parameters": {}}
        result = agent._normalize_tool_call(parsed)
        assert result == {"tool": "get_time", "args": {}}

    def test_normalize_tool_call_format3(self):
        agent = Agent()
        parsed = {"name": "get_time", "arguments": {}}
        result = agent._normalize_tool_call(parsed)
        assert result == {"tool": "get_time", "args": {}}

    def test_normalize_tool_call_invalid(self):
        agent = Agent()
        assert agent._normalize_tool_call({"foo": "bar"}) is None
        assert agent._normalize_tool_call({"tool": "get_time"}) is None

    def test_try_parse_json_tool_call_markdown_block(self):
        agent = Agent()
        content = '''```json
{"tool": "get_time", "args": {}}
```'''
        result = agent._try_parse_json_tool_call(content)
        assert result == {"tool": "get_time", "args": {}}

    def test_try_parse_json_tool_call_plain(self):
        agent = Agent()
        content = '{"tool": "get_time", "args": {}}'
        result = agent._try_parse_json_tool_call(content)
        assert result == {"tool": "get_time", "args": {}}

    def test_try_parse_json_tool_call_with_args(self):
        agent = Agent()
        content = '{"tool": "set_timer", "args": {"duration_minutes": 5, "label": "Test"}}'
        result = agent._try_parse_json_tool_call(content)
        assert result["tool"] == "set_timer"
        assert result["args"]["duration_minutes"] == 5

    def test_try_parse_json_tool_call_nested(self):
        agent = Agent()
        content = '{"tool": "set_timer", "args": {"nested": {"key": "value"}}}'
        result = agent._try_parse_json_tool_call(content)
        assert result is not None
        assert result["args"]["nested"]["key"] == "value"

    def test_try_parse_json_tool_call_invalid(self):
        agent = Agent()
        assert agent._try_parse_json_tool_call("not json") is None
        assert agent._try_parse_json_tool_call("") is None

    def test_try_parse_json_tool_call_openai_format(self):
        agent = Agent()
        content = '{"name": "get_time", "arguments": {}}'
        result = agent._try_parse_json_tool_call(content)
        assert result == {"tool": "get_time", "args": {}}

    @pytest.mark.asyncio
    async def test_run_native_tool_call(self):
        """Test run() with native tool calling."""
        agent = Agent()

        # Mock client.chat to return a tool call then a final response
        call_count = [0]

        class MockResponse:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        async def mock_chat(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: return tool call
                return MockResponse(
                    content="",
                    tool_calls=[{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_time", "arguments": "{}"}
                    }]
                )
            else:
                # Second call: return final response
                return MockResponse(content="Sekarang pukul 10:30")

        agent.client.chat = mock_chat

        # Mock registry.call
        original_call = agent.registry.call
        agent.registry.call = MagicMock(return_value="10:30")

        result = await agent.run("Jam berapa?")

        assert "10:30" in result or "pukul" in result
        agent.registry.call = original_call

    @pytest.mark.asyncio
    async def test_run_fallback_mode(self):
        """Test run() with fallback JSON parsing."""
        agent = Agent()
        agent._supports_native_tools = False  # Force fallback mode

        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.tool_calls = None

        call_count = [0]

        async def mock_chat(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: return tool call JSON
                return MockResponse('{"tool": "get_time", "args": {}}')
            else:
                # Second call: return final response after tool execution
                return MockResponse("Sekarang pukul 10:30")

        agent.client.chat = mock_chat
        original_call = agent.registry.call
        agent.registry.call = MagicMock(return_value="10:30")

        result = await agent.run("Jam berapa?")

        assert "10:30" in result or "pukul" in result or "pukul" in result.lower()
        agent.registry.call = original_call

    @pytest.mark.asyncio
    async def test_run_no_tool_call(self):
        """Test run() when model doesn't call any tool."""
        agent = Agent()

        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.tool_calls = None

        async def mock_chat(*args, **kwargs):
            return MockResponse("Halo! Ada yang bisa aku bantu?")

        agent.client.chat = mock_chat

        result = await agent.run("Halo")
        assert "Halo" in result

    @pytest.mark.asyncio
    async def test_run_stream_native(self):
        """Test run_stream() with native tool calling."""
        agent = Agent()

        class MockChunk:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        class MockStream:
            def __init__(self):
                self.chunks = [
                    MockChunk(content="Sekarang "),
                    MockChunk(content="pukul "),
                    MockChunk(content="10:30"),
                ]
                self.idx = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.idx < len(self.chunks):
                    chunk = self.chunks[self.idx]
                    self.idx += 1
                    return chunk
                raise StopAsyncIteration

        async def mock_chat(*args, **kwargs):
            return MockStream()

        agent.client.chat = mock_chat

        chunks = []
        async for chunk in agent.run_stream("Jam berapa?"):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert "".join(chunks) == "Sekarang pukul 10:30"

    @pytest.mark.asyncio
    async def test_run_stream_with_tool_calls(self):
        """Test run_stream() accumulating tool calls."""
        agent = Agent()
        agent._supports_native_tools = True

        class MockChunk:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        class MockStream:
            def __init__(self):
                self.idx = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.idx == 0:
                    self.idx += 1
                    return MockChunk(
                        content="",
                        tool_calls=[{
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_time", "arguments": "{}"}
                        }]
                    )
                else:
                    raise StopAsyncIteration

        async def mock_chat(*args, **kwargs):
            return MockStream()

        agent.client.chat = mock_chat
        original_call = agent.registry.call
        agent.registry.call = MagicMock(return_value="10:30")

        # In streaming mode with tool calls, it should execute and continue
        chunks = []
        async for chunk in agent.run_stream("Jam berapa?"):
            chunks.append(chunk)

        # Should have executed the tool
        assert agent.registry.call.called
        agent.registry.call = original_call

    @pytest.mark.asyncio
    async def test_run_stream_fallback_mode(self):
        """Test run_stream() in fallback mode (no native tools)."""
        agent = Agent()
        agent._supports_native_tools = False

        class MockResponse:
            def __init__(self, content):
                self.content = content

        async def mock_chat(*args, **kwargs):
            return MockResponse("Halo! Apa kabar?")

        agent.client.chat = mock_chat

        chunks = []
        async for chunk in agent.run_stream("Halo"):
            chunks.append(chunk)

        # Should yield the response in chunks
        full = "".join(chunks)
        assert "Halo" in full or "kabar" in full

    @pytest.mark.asyncio
    async def test_run_max_iterations(self):
        """Test run() stops after max_iterations."""
        agent = Agent(max_iterations=2)

        class MockResponse:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        call_count = [0]

        async def mock_chat(*args, **kwargs):
            call_count[0] += 1
            # Always return a tool call to force max iterations
            return MockResponse(
                content="",
                tool_calls=[{
                    "id": f"call_{call_count[0]}",
                    "type": "function",
                    "function": {"name": "get_time", "arguments": "{}"}
                }]
            )

        agent.client.chat = mock_chat
        original_call = agent.registry.call
        agent.registry.call = MagicMock(return_value="10:30")

        result = await agent.run("Test")

        # Should stop after max_iterations (2) and return overflow message
        assert "terlalu banyak iterasi" in result.lower() or "iterasi" in result.lower()
        agent.registry.call = original_call

    @pytest.mark.asyncio
    async def test_run_tool_error_handling(self):
        """Test run() handles tool execution errors."""
        agent = Agent()

        class MockResponse:
            def __init__(self, content=None, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        call_count = [0]

        async def mock_chat(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MockResponse(
                    content="",
                    tool_calls=[{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_time", "arguments": "{}"}
                    }]
                )
            else:
                # After tool error, model returns fallback response
                return MockResponse(content="Maaf, terjadi kesalahan.")

        agent.client.chat = mock_chat
        original_call = agent.registry.call
        agent.registry.call = MagicMock(side_effect=Exception("Tool error"))

        result = await agent.run("Jam berapa?")

        # Should return error message (tool error was handled)
        assert "error" in result.lower() or "gagal" in result.lower() or "kesalahan" in result.lower()
        agent.registry.call = original_call

    def test_map_tool_params(self):
        agent = Agent()
        # set_volume expects 'level' but model might send 'volume'
        mapped = agent._map_tool_params("set_volume", {"volume": 50})
        assert mapped == {"level": 50}

        # open_app expects 'app_name' but model might send 'app'
        mapped = agent._map_tool_params("open_app", {"app": "notepad"})
        assert mapped == {"app_name": "notepad"}

        # Unknown tool passes through
        mapped = agent._map_tool_params("unknown", {"foo": "bar"})
        assert mapped == {"foo": "bar"}

    def test_tools_property_lazy_load(self):
        agent = Agent()
        # First access loads tools
        tools1 = agent.tools
        assert len(tools1) > 0
        # Second access returns cached
        tools2 = agent.tools
        assert tools1 is tools2


class TestAgentSingleton:
    """Test global agent singleton."""

    def test_get_agent_singleton(self):
        reset_agent()
        a1 = get_agent()
        a2 = get_agent()
        assert a1 is a2
        reset_agent()


class TestAgentIntegration:
    """Integration-style tests with mocked components."""

    @pytest.mark.asyncio
    async def test_run_conversation_with_history(self):
        """Test run() includes conversation history."""
        agent = Agent()

        class MockResponse:
            def __init__(self, content):
                self.content = content
                self.tool_calls = None

        call_history = []

        async def mock_chat(messages, **kwargs):
            call_history.append(messages)
            return MockResponse("Terima kasih!")

        agent.client.chat = mock_chat

        history = [
            {"role": "user", "content": "Nama saya Akii"},
            {"role": "assistant", "content": "Halo Akii!"},
        ]
        result = await agent.run("Siapa namaku?", history=history)

        # Check that history was passed to the model
        assert len(call_history) == 1
        msgs = call_history[0]
        assert len(msgs) == 4  # system + 2 history + user
        assert msgs[1]["content"] == "Nama saya Akii"
        assert msgs[2]["content"] == "Halo Akii!"