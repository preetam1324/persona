"""Agent base class — override for custom behavior."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from persona.core.config import PersonaConfig
    from persona.core.response import AgentResponse, StreamChunk


class ConversationContext:
    """Context passed to agent handle/stream methods."""

    def __init__(self, session_id: str, history: list | None = None):
        self.session_id = session_id
        self.history: list = history or []


class Agent:
    """Base agent class. Override methods for custom behavior.

    For simple agents, this class is used as-is — behavior is driven
    entirely by config.yaml (system_prompt + tools + model).
    """

    def __init__(self, config: "PersonaConfig", secrets: dict[str, str], data_dir: Path):
        self.config = config
        self.secrets = secrets
        self.data_dir = data_dir

    def load(self) -> None:
        """Called once on startup. Override to load custom resources."""
        pass

    async def handle(
        self, message: str, context: ConversationContext
    ) -> "AgentResponse":
        """Process a user message. Default implementation uses AgentRuntime.

        Override this for full control over the agent loop.
        """
        raise NotImplementedError(
            "Default handle() is provided by AgentRuntime, not the base class."
        )

    async def stream(
        self, message: str, context: ConversationContext
    ) -> AsyncIterator["StreamChunk"]:
        """Streaming variant. Default implementation uses AgentRuntime."""
        raise NotImplementedError(
            "Default stream() is provided by AgentRuntime, not the base class."
        )
        yield  # make it a generator  # noqa: RET503
