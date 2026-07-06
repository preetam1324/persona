"""Tool interface and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Result of a tool execution."""

    output: Any
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class Tool(ABC):
    """Base class for all tools (builtin and custom)."""

    name: str = ""
    description: str = ""
    parameters: dict[str, Any] = {}  # JSON Schema for function calling

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments."""
        ...

    def to_schema(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry for discovering and instantiating tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI-compatible schemas for all registered tools."""
        return [tool.to_schema() for tool in self._tools.values()]
