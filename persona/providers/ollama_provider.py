"""Ollama provider adapter — for local models."""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from persona.core.provider import LLMChunk, LLMProvider, LLMResponse, ProviderRegistry
from persona.core.response import Message, UsageInfo


class OllamaProvider(LLMProvider):
    """Adapter for Ollama local models (llama3, mistral, phi3, gemma, etc.)."""

    def __init__(self, model_name: str, parameters: dict[str, Any], secrets: dict[str, str]):
        super().__init__(model_name, parameters, secrets)
        self.base_url = parameters.pop("base_url", "http://localhost:11434")

    def _format_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert to Ollama chat format."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "stream": False,
            "options": {k: v for k, v in self.parameters.items()},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        message = data.get("message", {})
        tool_calls = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                import json

                tool_calls.append({
                    "id": f"call_{tc['function']['name']}",
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.dumps(tc["function"].get("arguments", {})),
                    },
                })

        usage = None
        if "eval_count" in data:
            usage = UsageInfo(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
            )

        return LLMResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            usage=usage,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "stream": True,
            "options": {k: v for k, v in self.parameters.items()},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                import json

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    message = data.get("message", {})
                    content = message.get("content")
                    done = data.get("done", False)

                    yield LLMChunk(
                        content=content if content else None,
                        finish_reason="stop" if done else None,
                    )


# Register
ProviderRegistry.register("ollama", OllamaProvider)
