"""LLM Provider interface and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from persona.core.response import Message, UsageInfo


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: UsageInfo | None = None
    finish_reason: str | None = None


@dataclass
class LLMChunk:
    """A streaming chunk from an LLM provider."""

    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model_name: str, parameters: dict[str, Any], secrets: dict[str, str]):
        self.model_name = model_name
        self.parameters = parameters
        self.secrets = secrets

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send messages and get a complete response."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Send messages and get a streaming response."""
        ...
        yield  # type: ignore


class ProviderRegistry:
    """Registry for LLM provider classes."""

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a provider class by name."""
        cls._providers[name] = provider_class

    @classmethod
    def get(cls, name: str) -> type[LLMProvider] | None:
        """Get a provider class by name."""
        return cls._providers.get(name)

    @classmethod
    def create(
        cls,
        provider_name: str,
        model_name: str,
        parameters: dict[str, Any],
        secrets: dict[str, str],
    ) -> LLMProvider:
        """Create a provider instance."""
        provider_class = cls._providers.get(provider_name)
        if provider_class is None:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available: {available}"
            )
        return provider_class(model_name=model_name, parameters=parameters, secrets=secrets)
