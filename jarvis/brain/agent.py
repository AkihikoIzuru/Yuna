"""Agent loop: pesan -> LLM -> tool call -> hasil -> jawaban."""

import json
import logging
import re
from typing import Any, AsyncIterator, Optional

from jarvis.brain.client import RouterClient, ModelResponse, get_client
from jarvis.brain.prompts import get_system_prompt, format_tool_description
from jarvis.config import get_config
from jarvis.tools.registry import get_openai_tools, get_registry

logger = logging.getLogger(__name__)


class Agent:
    """Agent utama Jarvis dengan loop tool calling."""

    def __init__(
        self,
        client: Optional[RouterClient] = None,
        max_iterations: int = 5,
        enable_fallback: bool = True,
    ):
        self.client = client or get_client()
        self.max_iterations = max_iterations
        self.enable_fallback = enable_fallback
        self.registry = get_registry()

        # Load tools
        self.tools = get_openai_tools()
        self._supports_native_tools = True  # akan di-detect di runtime

    def _build_messages(self, user_message: str, history: Optional[list[dict]] = None) -> list[dict]:
        """Bangun messages untuk LLM."""
        messages = [{"role": "system", "content": get_system_prompt()}]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_message})
        return messages

    def _try_parse_json_tool_call(self, content: str) -> Optional[dict]:
        """
        Coba parse tool call dari konten teks (fallback mode).
        Format: {"tool": "nama", "args": {...}}
        """
        if not content:
            return None

        # Cari JSON di dalam konten
        patterns = [
            r'\{[^{}]*"tool"\s*:\s*"[^"]+"[^{}]*\}',  # simple JSON
            r'```json\s*(\{.*?\})\s*```',  # markdown code block
            r'```\s*(\{.*?\})\s*```',  # generic code block
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if "tool" in parsed and "args" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue

        return None

    async def _execute_tool(self, tool_call: dict) -> dict:
        """Eksekusi tool call dan return result."""
        name = tool_call["function"]["name"]
        args = self.client.parse_tool_arguments(tool_call)

        logger.info(f"Executing tool: {name} with args: {args}")

        try:
            result = self.registry.call(name, args)
            return {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result),
            }
        except Exception as e:
            logger.error(f"Tool '{name}' error: {e}")
            return {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": f"Error: {e}",
            }

    async def _execute_fallback_tool(self, tool_name: str, args: dict) -> str:
        """Eksekusi tool untuk fallback mode."""
        try:
            result = self.registry.call(tool_name, args)
            return str(result)
        except Exception as e:
            logger.error(f"Fallback tool '{tool_name}' error: {e}")
            return f"Error: {e}"

    async def run(self, user_message: str, history: Optional[list[dict]] = None) -> str:
        """
        Jalankan agent untuk satu percakapan (non-streaming).

        Returns:
            Final response dari assistant.
        """
        messages = self._build_messages(user_message, history)

        for iteration in range(self.max_iterations):
            # Coba native tool calling dulu
            if self._supports_native_tools and self.tools:
                response = await self.client.chat(
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.3,
                )

                # Cek apakah model support native tools
                if response.tool_calls is None and iteration == 0:
                    # Model mungkin tidak support tools, coba fallback
                    logger.info("Model tidak return tool_calls, coba fallback mode")
                    self._supports_native_tools = False
                elif response.tool_calls:
                    # Ada tool calls, eksekusi
                    messages.append({
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": response.tool_calls,
                    })

                    for tc in response.tool_calls:
                        tool_result = await self._execute_tool(tc)
                        messages.append(tool_result)

                    continue  # lanjut iterasi untuk response berikutnya

                # Tidak ada tool calls, return content
                return response.content or "Maaf, saya tidak mengerti."

            # Fallback mode: model diminta balas JSON
            fallback_prompt = format_tool_description(self.tools)
            messages_with_fallback = messages + [{"role": "system", "content": fallback_prompt}]

            response = await self.client.chat(
                messages=messages_with_fallback,
                temperature=0.3,
            )

            # Coba parse tool call dari content
            parsed = self._try_parse_json_tool_call(response.content or "")

            if parsed:
                tool_name = parsed["tool"]
                args = parsed["args"]

                # Eksekusi tool
                result = await self._execute_fallback_tool(tool_name, args)

                # Tambahkan ke messages untuk iterasi berikutnya
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": f"Tool result: {result}"})
                continue

            # Tidak ada tool call, return response
            return response.content or "Maaf, saya tidak mengerti."

        return "Maaf, terlalu banyak iterasi. Coba ulangi pertanyaan Anda."

    async def run_stream(self, user_message: str, history: Optional[list[dict]] = None) -> AsyncIterator[str]:
        """
        Jalankan agent dengan streaming response.
        Yields content chunks.
        """
        messages = self._build_messages(user_message, history)

        for iteration in range(self.max_iterations):
            if self._supports_native_tools and self.tools:
                stream = await self.client.chat(
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.3,
                    stream=True,
                )

                accumulated_content = ""
                accumulated_tool_calls: dict[int, dict] = {}

                async for chunk in stream:
                    if chunk.content:
                        accumulated_content += chunk.content
                        yield chunk.content

                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            idx = tc.get("index", 0)
                            if idx not in accumulated_tool_calls:
                                accumulated_tool_calls[idx] = tc
                            else:
                                # Merge incremental tool call
                                if tc.get("function", {}).get("name"):
                                    accumulated_tool_calls[idx]["function"]["name"] += tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    accumulated_tool_calls[idx]["function"]["arguments"] += tc["function"]["arguments"]

                # Cek apakah ada tool calls
                if accumulated_tool_calls:
                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": accumulated_content,
                        "tool_calls": list(accumulated_tool_calls.values()),
                    })

                    # Execute each tool
                    for tc in accumulated_tool_calls.values():
                        tool_result = await self._execute_tool(tc)
                        messages.append(tool_result)

                    continue  # lanjut iterasi

                # Tidak ada tool calls, done
                return

            # Fallback streaming - tidak support native, fallback ke non-stream
            response = await self.client.chat(
                messages=messages + [{"role": "system", "content": format_tool_description(self.tools)}],
                temperature=0.3,
                stream=False,
            )

            parsed = self._try_parse_json_tool_call(response.content or "")

            if parsed:
                tool_name = parsed["tool"]
                args = parsed["args"]
                result = await self._execute_fallback_tool(tool_name, args)

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": f"Tool result: {result}"})
                continue

            # Stream the response content
            if response.content:
                # Simulate streaming by yielding in chunks
                for chunk in [response.content[i:i+50] for i in range(0, len(response.content), 50)]:
                    yield chunk
            return

        yield "Maaf, terlalu banyak iterasi."


# Global agent instance
_agent: Optional[Agent] = None


def get_agent() -> Agent:
    """Get global agent instance."""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent