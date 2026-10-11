"""Tests untuk RouterClient."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from jarvis.brain.client import RouterClient, ModelResponse


@pytest.fixture
def mock_async_openai():
    """Mock AsyncOpenAI class and its methods."""
    with patch("jarvis.brain.client.AsyncOpenAI") as mock_class:
        mock_instance = Mock()
        mock_instance.chat.completions.create = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


def test_client_init():
    """Test inisialisasi client."""
    c = RouterClient(
        base_url="http://localhost:20128/v1",
        api_key="sk-test",
        model="jarvis",
        fast_model="jarvis-fast",
    )
    assert c.base_url == "http://localhost:20128/v1"
    assert c.model == "jarvis"
    assert c.fast_model == "jarvis-fast"
    assert c.api_key == "sk-test"


@pytest.mark.asyncio
async def test_chat_success(mock_async_openai):
    """Test chat completion sukses."""
    client = RouterClient(
        base_url="http://test.local/v1",
        api_key="test-key",
        model="test-model",
        fast_model="fast-model",
        timeout=30.0,
    )

    # Mock response
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = "Halo!"
    mock_choice.message.tool_calls = None
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]
    mock_response.model = "jarvis"
    mock_response.usage = Mock()
    mock_response.usage.model_dump.return_value = {"total_tokens": 10}

    mock_async_openai.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await client.chat(
        messages=[{"role": "user", "content": "Halo"}],
        temperature=0.3,
    )

    assert isinstance(result, ModelResponse)
    assert result.content == "Halo!"
    assert result.tool_calls is None
    assert result.finish_reason == "stop"


@pytest.mark.asyncio
async def test_chat_with_tool_calls(mock_async_openai):
    """Test chat dengan tool calls."""
    client = RouterClient(
        base_url="http://test.local/v1",
        api_key="test-key",
        model="test-model",
        fast_model="fast-model",
        timeout=30.0,
    )

    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = "Cek cuaca..."

    mock_tool_call = Mock()
    mock_tool_call.id = "call_123"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "get_weather"
    mock_tool_call.function.arguments = '{"city": "Jakarta"}'

    mock_choice.message.tool_calls = [mock_tool_call]
    mock_choice.finish_reason = "tool_calls"
    mock_response.choices = [mock_choice]
    mock_response.model = "jarvis"
    mock_response.usage = None

    mock_async_openai.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await client.chat(
        messages=[{"role": "user", "content": "Cuaca Jakarta gimana?"}],
        tools=[{"type": "function", "function": {"name": "get_weather"}}],
    )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["function"]["name"] == "get_weather"


@pytest.mark.asyncio
async def test_chat_fallback_on_error(mock_async_openai):
    """Test fallback ke fast_model saat error."""
    client = RouterClient(
        base_url="http://test.local/v1",
        api_key="test-key",
        model="test-model",
        fast_model="fast-model",
        timeout=30.0,
        max_retries=1,
    )

    # First call fails, second succeeds
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = "Fallback response"
    mock_choice.message.tool_calls = None
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]
    mock_response.model = "fast-model"
    mock_response.usage = None

    mock_async_openai.chat.completions.create = AsyncMock(
        side_effect=[Exception("Model error"), mock_response]
    )

    result = await client.chat(
        messages=[{"role": "user", "content": "Test"}],
    )

    assert result.content == "Fallback response"
    assert result.model == "fast-model"
    assert mock_async_openai.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_parse_tool_arguments():
    """Test parse tool arguments."""
    client = RouterClient(
        base_url="http://test.local/v1",
        api_key="test",
        model="test",
        fast_model="test",
    )

    # String JSON
    tool_call = {
        "function": {"name": "test", "arguments": '{"city": "Jakarta"}'},
    }
    args = client.parse_tool_arguments(tool_call)
    assert args == {"city": "Jakarta"}

    # Already dict
    tool_call2 = {
        "function": {"name": "test", "arguments": {"city": "Bandung"}},
    }
    args2 = client.parse_tool_arguments(tool_call2)
    assert args2 == {"city": "Bandung"}

    # Invalid JSON
    tool_call3 = {
        "function": {"name": "test", "arguments": "not json"},
    }
    args3 = client.parse_tool_arguments(tool_call3)
    assert args3 == {}


@pytest.mark.asyncio
async def test_close_client(mock_async_openai):
    """Test close client."""
    client = RouterClient(
        base_url="http://test.local/v1",
        api_key="test-key",
        model="test-model",
        fast_model="fast-model",
        timeout=30.0,
    )

    mock_close = AsyncMock()
    client._client.close = mock_close

    await client.close()
    mock_close.assert_called_once()