"""Response types for agent interactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRecord:
    """Record of a tool invocation during agent processing."""

    tool: str
    input: dict[str, Any]
    output: Any = None
    error: str | None = None


@dataclass
class UsageInfo:
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class AgentResponse:
    """Complete response from an agent."""

    response: str
    session_id: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    usage: UsageInfo | None = None


@dataclass
class StreamChunk:
    """A single chunk in a streaming response."""

    type: str  # "token", "tool_call", "tool_result", "done", "error"
    content: str | None = None
    tool: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: Any = None
    usage: UsageInfo | None = None


@dataclass
class Message:
    """A message in a conversation."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    name: str | None = None
