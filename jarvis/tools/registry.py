"""Registry tools dengan decorator @tool dan auto-discovery JSON schema."""

import inspect
import json
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, get_type_hints

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Representasi tool yang terdaftar."""
    name: str
    func: Callable
    description: str
    parameters: dict
    risk: str = "low"  # low, medium, high


class ToolRegistry:
    """Registry untuk mengelola tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, func: Callable, risk: str = "low") -> Tool:
        """Register sebuah fungsi sebagai tool."""
        name = func.__name__
        description = func.__doc__ or f"Tool {name}"

        # Auto-generate JSON schema dari type hints + signature
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = type_hints.get(param_name, Any)
            param_schema = self._type_to_schema(param_type)

            # Handle default values
            if param.default != inspect.Parameter.empty:
                param_schema["default"] = param.default
            else:
                required.append(param_name)

            properties[param_name] = param_schema

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

        tool = Tool(
            name=name,
            func=func,
            description=description.strip(),
            parameters=parameters,
            risk=risk,
        )

        self._tools[name] = tool
        logger.debug(f"Registered tool: {name} (risk={risk})")
        return tool

    def _type_to_schema(self, typ: Any) -> dict:
        """Konversi Python type hint ke JSON Schema."""
        # Handle Optional[T] = Union[T, None]
        if hasattr(typ, "__origin__") and typ.__origin__ is type(None):
            return {"type": "null"}

        if hasattr(typ, "__origin__"):
            origin = typ.__origin__
            args = typ.__args__

            if origin is list or origin is list:
                item_schema = self._type_to_schema(args[0]) if args else {}
                return {"type": "array", "items": item_schema}

            if origin is dict or origin is dict:
                return {"type": "object"}

            if origin is tuple:
                items = [self._type_to_schema(a) for a in args]
                return {"type": "array", "items": {"anyOf": items}}

            # Union (including Optional)
            if origin is type(None):  # handled above
                pass
            if str(origin).startswith("typing.Union") or str(origin).startswith("types.Union"):
                schemas = [self._type_to_schema(a) for a in args]
                return {"anyOf": schemas}

        # Basic types
        if typ is str:
            return {"type": "string"}
        if typ is int:
            return {"type": "integer"}
        if typ is float:
            return {"type": "number"}
        if typ is bool:
            return {"type": "boolean"}
        if typ is type(None):
            return {"type": "null"}

        # Default
        return {"type": "string"}

    def get_tool(self, name: str) -> Tool | None:
        """Get tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_openai_tools(self) -> list[dict]:
        """Get tools dalam format OpenAI function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def call(self, name: str, args: dict) -> Any:
        """Call tool by name dengan arguments."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' tidak ditemukan")
        return tool.func(**args)

    def call_async(self, name: str, args: dict) -> Any:
        """Call async tool by name."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' tidak ditemukan")
        return tool.func(**args)


# Global registry instance
_registry = ToolRegistry()


def tool(risk: str = "low"):
    """
    Decorator untuk register fungsi sebagai tool.

    Args:
        risk: Tingkat risiko - "low", "medium", "high"

    Contoh:
        @tool(risk="low")
        def get_time() -> str:
            '''Dapatkan waktu saat ini.'''
            return datetime.now().strftime("%H:%M")
    """
    def decorator(func: Callable) -> Callable:
        _registry.register(func, risk=risk)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator


def get_registry() -> ToolRegistry:
    """Get global tool registry."""
    return _registry


def get_openai_tools() -> list[dict]:
    """Get all tools dalam format OpenAI."""
    return _registry.get_openai_tools()