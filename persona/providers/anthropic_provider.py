"""Anthropic provider adapter."""

from __future__ import annotations

from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic

from persona.core.provider import LLMChunk, LLMProvider, LLMResponse, ProviderRegistry
from persona.core.response import Message, UsageInfo


class AnthropicProvider(LLMProvider):
    """Adapter for Anthropic API (Claude Sonnet, Haiku, Opus)."""

    def __init__(self, model_name: str, parameters: dict[str, Any], secrets: dict[str, str]):
        super().__init__(model_name, parameters, secrets)
        api_key = secrets.get("ANTHROPIC_API_KEY", "")
        self.client = AsyncAnthropic(api_key=api_key)

    def _format_messages(self, messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
        """Split system prompt from messages for Anthropic's API format."""
        system = ""
        formatted = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
            elif msg.role == "tool":
                formatted.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                })
            elif msg.role == "assistant" and msg.tool_calls:
                # Convert tool calls to Anthropic's tool_use format
                content: list[dict[str, Any]] = []
                if msg.content:
                    content.append({"type": "text", "text": msg.content})
                for tc in msg.tool_calls:
                    import json

                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "input": json.loads(tc["function"]["arguments"]),
                    })
                formatted.append({"role": "assistant", "content": content})
            else:
                formatted.append({"role": msg.role, "content": msg.content})

        return system, formatted

    def _convert_tools(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert OpenAI tool format to Anthropic format."""
        if not tools:
            return None
        anthropic_tools = []
        for tool in tools:
            fn = tool["function"]
            anthropic_tools.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        system, formatted = self._format_messages(messages)
        params = {**self.parameters}
        max_tokens = params.pop("max_tokens", 4096)

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted,
            "max_tokens": max_tokens,
            **params,
        }
        if system:
            kwargs["system"] = system

        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        response = await self.client.messages.create(**kwargs)

        content_text = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                import json

                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        usage = UsageInfo(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
        )

        finish_reason = "stop" if response.stop_reason == "end_turn" else response.stop_reason

        return LLMResponse(
            content=content_text or None,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=finish_reason,
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        system, formatted = self._format_messages(messages)
        params = {**self.parameters}
        max_tokens = params.pop("max_tokens", 4096)

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted,
            "max_tokens": max_tokens,
            **params,
        }
        if system:
            kwargs["system"] = system

        anthropic_tools = self._convert_tools(tools)
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield LLMChunk(content=event.delta.text)
                        elif hasattr(event.delta, "partial_json"):
                            # Tool input streaming — accumulate externally
                            yield LLMChunk(content=None)
                    elif event.type == "message_stop":
                        yield LLMChunk(finish_reason="stop")


# Register
ProviderRegistry.register("anthropic", AnthropicProvider)
