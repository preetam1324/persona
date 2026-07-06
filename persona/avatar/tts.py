"""TTS provider abstraction and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Viseme:
    """A single viseme (mouth shape) event."""

    id: str  # e.g. "aa", "oh", "ee", "ss", "th", "silence"
    start_ms: int
    duration_ms: int


@dataclass
class TTSChunk:
    """A chunk of synthesized audio with optional viseme data."""

    audio: bytes  # PCM or opus-encoded audio bytes
    format: str = "pcm"  # "pcm", "opus", "mp3"
    sample_rate: int = 24000
    visemes: list[Viseme] = field(default_factory=list)
    is_final: bool = False


class TTSProvider(ABC):
    """Abstract TTS provider — streams audio chunks for given text."""

    @abstractmethod
    async def synthesize(self, text: str) -> TTSChunk:
        """Synthesize full text into a single audio chunk."""
        ...

    @abstractmethod
    async def stream(self, text: str) -> AsyncIterator[TTSChunk]:
        """Stream audio chunks as they are generated."""
        ...

    @abstractmethod
    def supported_voices(self) -> list[str]:
        """Return list of supported voice IDs."""
        ...


class TTSProviderRegistry:
    """Registry for TTS providers."""

    _providers: dict[str, type[TTSProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[TTSProvider]) -> None:
        cls._providers[name] = provider_cls

    @classmethod
    def get(cls, name: str, **kwargs) -> TTSProvider:
        if name not in cls._providers:
            raise ValueError(
                f"Unknown TTS provider: {name}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[name](**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._providers.keys())


# Auto-register providers on import
def _register_providers() -> None:
    try:
        from persona.avatar.providers.openai_tts import OpenAITTSProvider

        TTSProviderRegistry.register("openai", OpenAITTSProvider)
    except ImportError:
        pass


_register_providers()
