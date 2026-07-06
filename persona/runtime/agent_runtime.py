"""AgentRuntime — the think→act execution loop."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from persona.core.agent import Agent, ConversationContext
from persona.core.config import PersonaConfig
from persona.core.provider import LLMProvider, ProviderRegistry
from persona.core.response import (
    AgentResponse,
    Message,
    StreamChunk,
    ToolCallRecord,
    UsageInfo,
)
from persona.core.tool import ToolRegistry
from persona.runtime.memory import ConversationMemory

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Orchestrates the agent loop: receive → prompt → LLM → tool → repeat → respond."""

    def __init__(
        self,
        config: PersonaConfig,
        provider: LLMProvider,
        tools: ToolRegistry,
        agent: Agent,
        memory: ConversationMemory,
    ):
        self.config = config
        self.provider = provider
        self.tools = tools
        self.agent = agent
        self.memory = memory
        self.max_turns = config.runtime.max_turns

    @classmethod
    def from_config(cls, config: PersonaConfig, secrets: dict[str, str]) -> "AgentRuntime":
        """Create a fully-wired AgentRuntime from a PersonaConfig."""
        from pathlib import Path

        from persona.tools.registry import build_tool_registry

        # Ensure providers are registered
        import persona.providers.registry  # noqa: F401

        # Create provider
        provider = ProviderRegistry.create(
            provider_name=config.agent.model.provider,
            model_name=config.agent.model.name,
            parameters={**config.agent.model.parameters},
            secrets=secrets,
        )

        # Create tools
        data_dir = Path("data")
        tools = build_tool_registry(config.agent.tools, data_dir=data_dir)

        # Create agent
        agent = Agent(config=config, secrets=secrets, data_dir=data_dir)
        agent.load()

        # Create memory
        memory = ConversationMemory()

        return cls(config=config, provider=provider, tools=tools, agent=agent, memory=memory)

    async def handle(self, message: str, session_id: str) -> AgentResponse:
        """Process a user message through the full agent loop."""
        context = ConversationContext(
            session_id=session_id,
            history=self.memory.get_messages(session_id),
        )

        # Build messages
        messages = self._build_messages(message, context)

        # Agent loop: LLM → tool call → LLM → ... → final response
        all_tool_calls: list[ToolCallRecord] = []
        total_usage = UsageInfo()

        for turn in range(self.max_turns):
            tool_schemas = self.tools.get_schemas() if self.tools.list_tools() else None
            response = await self.provider.complete(messages, tools=tool_schemas)

            # Accumulate usage
            if response.usage:
                total_usage.prompt_tokens += response.usage.prompt_tokens
                total_usage.completion_tokens += response.usage.completion_tokens

            # If no tool calls, we have the final response
            if not response.tool_calls:
                final_content = response.content or ""
                break

            # Process tool calls
            # Add assistant message with tool calls
            messages.append(Message(
                role="assistant",
                content=response.content or "",
                tool_calls=response.tool_calls,
            ))

            for tc in response.tool_calls:
                fn_name = tc["function"]["name"]
                fn_args_str = tc["function"]["arguments"]
                tc_id = tc.get("id", f"call_{fn_name}")

                try:
                    fn_args = json.loads(fn_args_str) if fn_args_str else {}
                except json.JSONDecodeError:
                    fn_args = {}

                # Execute tool
                tool = self.tools.get(fn_name)
                if tool is None:
                    result_str = f"Error: Unknown tool '{fn_name}'"
                    all_tool_calls.append(ToolCallRecord(
                        tool=fn_name, input=fn_args, error=result_str
                    ))
                else:
                    logger.info(f"Executing tool: {fn_name}({fn_args})")
                    result = await tool.execute(**fn_args)
                    result_str = str(result.output) if result.success else f"Error: {result.error}"
                    all_tool_calls.append(ToolCallRecord(
                        tool=fn_name,
                        input=fn_args,
                        output=result.output if result.success else None,
                        error=result.error,
                    ))

                # Add tool result message
                messages.append(Message(
                    role="tool",
                    content=result_str,
                    tool_call_id=tc_id,
                    name=fn_name,
                ))
        else:
            # Hit max turns — take whatever we have
            final_content = response.content or "I was unable to complete the task within the allowed steps."

        # Save to memory
        self.memory.add_message(session_id, Message(role="user", content=message))
        self.memory.add_message(session_id, Message(role="assistant", content=final_content))

        return AgentResponse(
            response=final_content,
            session_id=session_id,
            tool_calls=all_tool_calls,
            usage=total_usage,
        )

    async def stream(self, message: str, session_id: str) -> AsyncIterator[StreamChunk]:
        """Stream a response token-by-token with tool call events."""
        context = ConversationContext(
            session_id=session_id,
            history=self.memory.get_messages(session_id),
        )
        messages = self._build_messages(message, context)

        for turn in range(self.max_turns):
            tool_schemas = self.tools.get_schemas() if self.tools.list_tools() else None

            # Stream from LLM
            collected_content = ""
            collected_tool_calls: list[dict[str, Any]] = []
            tool_call_buffers: dict[int, dict[str, str]] = {}

            async for chunk in self.provider.stream(messages, tools=tool_schemas):
                if chunk.content:
                    collected_content += chunk.content
                    yield StreamChunk(type="token", content=chunk.content)

                if chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        idx = tc.get("index", 0)
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {
                                "id": tc.get("id", ""),
                                "name": "",
                                "arguments": "",
                            }
                        if tc.get("id"):
                            tool_call_buffers[idx]["id"] = tc["id"]
                        fn = tc.get("function", {})
                        if fn.get("name"):
                            tool_call_buffers[idx]["name"] = fn["name"]
                        if fn.get("arguments"):
                            tool_call_buffers[idx]["arguments"] += fn["arguments"]

                if chunk.finish_reason:
                    break

            # If no tool calls, we're done
            if not tool_call_buffers:
                self.memory.add_message(session_id, Message(role="user", content=message))
                self.memory.add_message(
                    session_id, Message(role="assistant", content=collected_content)
                )
                yield StreamChunk(type="done")
                return

            # Build tool calls from buffers
            for _idx, buf in sorted(tool_call_buffers.items()):
                collected_tool_calls.append({
                    "id": buf["id"],
                    "type": "function",
                    "function": {"name": buf["name"], "arguments": buf["arguments"]},
                })

            # Add assistant message
            messages.append(Message(
                role="assistant",
                content=collected_content,
                tool_calls=collected_tool_calls,
            ))

            # Execute tools
            for tc in collected_tool_calls:
                fn_name = tc["function"]["name"]
                fn_args_str = tc["function"]["arguments"]
                tc_id = tc.get("id", f"call_{fn_name}")

                yield StreamChunk(type="tool_call", tool=fn_name)

                try:
                    fn_args = json.loads(fn_args_str) if fn_args_str else {}
                except json.JSONDecodeError:
                    fn_args = {}

                tool = self.tools.get(fn_name)
                if tool:
                    result = await tool.execute(**fn_args)
                    result_str = str(result.output) if result.success else f"Error: {result.error}"
                else:
                    result_str = f"Error: Unknown tool '{fn_name}'"

                yield StreamChunk(type="tool_result", tool=fn_name, tool_output=result_str)

                messages.append(Message(
                    role="tool", content=result_str, tool_call_id=tc_id, name=fn_name
                ))

        # If we exhausted turns
        yield StreamChunk(type="done")

    def _build_messages(self, message: str, context: ConversationContext) -> list[Message]:
        """Build the full message list: system + history + current message."""
        messages: list[Message] = []

        # System prompt
        messages.append(Message(role="system", content=self.config.agent.system_prompt))

        # Conversation history
        messages.extend(context.history)

        # Current user message
        messages.append(Message(role="user", content=message))

        return messages
