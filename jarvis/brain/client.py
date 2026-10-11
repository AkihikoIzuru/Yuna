"""Klien 9Router (OpenAI-compatible) dengan retry, timeout, dan fallback model."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice

from jarvis.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """Response terstandarisasi dari model."""
    content: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    model: str = ""
    finish_reason: str = "stop"
    usage: Optional[dict] = None


class RouterClient:
    """Wrapper AsyncOpenAI untuk 9Router dengan fallback & retry."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fast_model: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        cfg = get_config()
        self.base_url = base_url or cfg.base_url
        self.api_key = api_key or cfg.api_key
        self.model = model or cfg.model
        self.fast_model = fast_model or cfg.fast_model
        self.timeout = timeout
        self.max_retries = max_retries

        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=timeout,
            max_retries=0,  # handle retry manual
        )

    async def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        stream: bool = False,
        model: Optional[str] = None,
    ) -> ModelResponse | AsyncIterator[ModelResponse]:
        """Kirim chat completion, dengan fallback ke fast_model jika gagal."""
        use_model = model or self.model

        for attempt in range(self.max_retries + 1):
            current_model = use_model if attempt == 0 else self.fast_model
            if attempt > 0:
                logger.warning(f"Fallback ke model cepat: {current_model} (attempt {attempt})")

            try:
                if stream:
                    return self._chat_stream(
                        messages, tools, tool_choice, temperature, max_tokens, current_model
                    )
                return await self._chat_once(
                    messages, tools, tool_choice, temperature, max_tokens, current_model
                )
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Semua model gagal setelah {self.max_retries + 1} percobaan: {e}")
                    raise
                await asyncio.sleep(0.5 * (2**attempt))  # exponential backoff

        raise RuntimeError("Unreachable")

    async def _chat_once(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        tool_choice: Optional[str | dict],
        temperature: float,
        max_tokens: int,
        model: str,
    ) -> ModelResponse:
        """Single non-streaming request."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        response: ChatCompletion = await self._client.chat.completions.create(**kwargs)
        choice: Choice = response.choices[0]

        return ModelResponse(
            content=choice.message.content,
            tool_calls=[
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (choice.message.tool_calls or [])
            ] if choice.message.tool_calls else None,
            model=response.model,
            finish_reason=choice.finish_reason,
            usage=response.usage.model_dump() if response.usage else None,
        )

    async def _chat_stream(
        self,
        messages: list[dict],
        tools: Optional[list[dict]],
        tool_choice: Optional[str | dict],
        temperature: float,
        max_tokens: int,
        model: str,
    ) -> AsyncIterator[ModelResponse]:
        """Streaming request."""
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        stream = await self._client.chat.completions.create(**kwargs)

        accumulated_content = ""
        accumulated_tool_calls: dict[int, dict] = {}

        async for chunk in stream:
            chunk_choice: ChunkChoice = chunk.choices[0]
            delta = chunk_choice.delta

            content_delta = delta.content or ""
            if content_delta:
                accumulated_content += content_delta

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in accumulated_tool_calls:
                        accumulated_tool_calls[idx] = {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.function.name:
                        accumulated_tool_calls[idx]["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        accumulated_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            yield ModelResponse(
                content=content_delta if content_delta else None,
                tool_calls=list(accumulated_tool_calls.values()) if accumulated_tool_calls else None,
                model=chunk.model,
                finish_reason=chunk_choice.finish_reason or "stop",
            )

    def parse_tool_arguments(self, tool_call: dict) -> dict:
        """Parse argumen tool call (handle string JSON)."""
        args = tool_call["function"]["arguments"]
        if isinstance(args, str):
            try:
                return json.loads(args)
            except json.JSONDecodeError:
                logger.warning(f"Gagal parse JSON tool args: {args}")
                return {}
        return args or {}

    async def close(self) -> None:
        """Tutup koneksi."""
        await self._client.close()


# Global client instance
_client: Optional[RouterClient] = None


def get_client() -> RouterClient:
    """Get global client instance."""
    global _client
    if _client is None:
        _client = RouterClient()
    return _client


async def close_client() -> None:
    """Close global client."""
    global _client
    if _client:
        await _client.close()
        _client = None