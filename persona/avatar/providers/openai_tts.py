"""OpenAI TTS provider — uses the openai.audio.speech API."""

from __future__ import annotations

import struct
from typing import AsyncIterator

from persona.avatar.tts import TTSChunk, TTSProvider, Viseme


# Simple phoneme-to-viseme mapping for lip sync approximation
_CHAR_VISEME_MAP = {
    "a": "aa",
    "e": "ee",
    "i": "ih",
    "o": "oh",
    "u": "oo",
    "s": "ss",
    "z": "ss",
    "f": "ff",
    "v": "ff",
    "t": "dd",
    "d": "dd",
    "n": "nn",
    "m": "mm",
    "p": "pp",
    "b": "pp",
    "r": "rr",
    "l": "nn",
    "w": "oo",
    "y": "ee",
    "h": "silence",
    " ": "silence",
}

# Average character duration in ms (150 WPM ~= 80ms per character)
_CHAR_DURATION_MS = 80


def _estimate_visemes(text: str) -> list[Viseme]:
    """Generate approximate visemes from text characters."""
    visemes = []
    offset = 0
    for ch in text.lower():
        vid = _CHAR_VISEME_MAP.get(ch, "silence")
        visemes.append(Viseme(id=vid, start_ms=offset, duration_ms=_CHAR_DURATION_MS))
        offset += _CHAR_DURATION_MS
    return visemes


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS-1 / TTS-1-HD provider."""

    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def __init__(
        self,
        voice_id: str = "alloy",
        speed: float = 1.0,
        model: str = "tts-1",
        api_key: str | None = None,
    ) -> None:
        self.voice_id = voice_id
        self.speed = speed
        self.model = model
        self._api_key = api_key

    def _get_client(self):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai package required for TTS. Install: pip install persona[avatar]"
            )
        kwargs = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        return AsyncOpenAI(**kwargs)

    async def synthesize(self, text: str) -> TTSChunk:
        """Synthesize full text into a single MP3 audio chunk."""
        client = self._get_client()
        response = await client.audio.speech.create(
            model=self.model,
            voice=self.voice_id,
            input=text,
            speed=self.speed,
            response_format="mp3",
        )
        audio_bytes = response.content
        visemes = _estimate_visemes(text)
        return TTSChunk(
            audio=audio_bytes,
            format="mp3",
            sample_rate=24000,
            visemes=visemes,
            is_final=True,
        )

    async def stream(self, text: str) -> AsyncIterator[TTSChunk]:
        """Stream audio chunks using OpenAI's streaming response."""
        client = self._get_client()
        response = await client.audio.speech.create(
            model=self.model,
            voice=self.voice_id,
            input=text,
            speed=self.speed,
            response_format="pcm",
        )
        # OpenAI returns full audio — split into chunks for streaming
        raw = response.content
        chunk_size = 4800  # 100ms at 24kHz 16-bit mono
        visemes = _estimate_visemes(text)
        total_chunks = max(1, len(raw) // chunk_size)
        visemes_per_chunk = max(1, len(visemes) // total_chunks)

        for i in range(0, len(raw), chunk_size):
            chunk_audio = raw[i : i + chunk_size]
            chunk_idx = i // chunk_size
            v_start = chunk_idx * visemes_per_chunk
            v_end = v_start + visemes_per_chunk
            chunk_visemes = visemes[v_start:v_end]

            yield TTSChunk(
                audio=chunk_audio,
                format="pcm",
                sample_rate=24000,
                visemes=chunk_visemes,
                is_final=(i + chunk_size >= len(raw)),
            )

    def supported_voices(self) -> list[str]:
        return self.VOICES
