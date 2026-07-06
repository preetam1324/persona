"""OpenAI provider adapter."""

from __future__ import annotations

from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from persona.core.provider import LLMChunk, LLMProvider, LLMResponse, ProviderRegistry
from persona.core.response import Message, UsageInfo


class OpenAIProvider(LLMProvider):
    """Adapter for OpenAI API (GPT-4o, GPT-4o-mini, o1, etc.)."""

    def __init__(self, model_name: str, parameters: dict[str, Any], secrets: dict[str, str]):
        super().__init__(model_name, parameters, secrets)
        api_key = secrets.get("OPENAI_API_KEY", "")
        base_url = parameters.pop("base_url", None)
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _format_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Convert internal Message format to OpenAI format."""
        formatted = []
        for msg in messages:
            m: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                m["name"] = msg.name
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            formatted.append(m)
        return formatted

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            **self.parameters,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        usage = None
        if response.usage:
            usage = UsageInfo(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
            finish_reason=choice.finish_reason,
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": self._format_messages(messages),
            "stream": True,
            **self.parameters,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.completions.create(**kwargs)

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason

            tool_calls = None
            if delta.tool_calls:
                tool_calls = []
                for tc in delta.tool_calls:
                    tool_calls.append({
                        "index": tc.index,
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name if tc.function else None,
                            "arguments": tc.function.arguments if tc.function else "",
                        },
                    })

            yield LLMChunk(
                content=delta.content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )


# Register
ProviderRegistry.register("openai", OpenAIProvider)
