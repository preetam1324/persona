"""HTTP endpoints — /v1/chat, /health, /ready, /v1/agent/info."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse


def create_router() -> APIRouter:
    """Create the API router with all endpoints."""
    router = APIRouter()

    class ChatRequest(BaseModel):
        message: str
        session_id: str | None = None
        stream: bool = False

    class ToolCallResponse(BaseModel):
        tool: str
        input: dict[str, Any] = Field(default_factory=dict)
        output: Any = None
        error: str | None = None

    class UsageResponse(BaseModel):
        prompt_tokens: int = 0
        completion_tokens: int = 0
        total_tokens: int = 0

    class ChatResponse(BaseModel):
        response: str
        session_id: str
        tool_calls: list[ToolCallResponse] = Field(default_factory=list)
        usage: UsageResponse | None = None

    @router.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe — always returns 200 if process is running."""
        return {"status": "ok"}

    @router.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        """Readiness probe — 200 only after agent is loaded."""
        is_ready = getattr(request.app.state, "ready", False)
        if is_ready:
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "loading"}, status_code=503)

    @router.get("/v1/agent/info")
    async def agent_info(request: Request) -> dict[str, Any]:
        """Return agent metadata."""
        config = request.app.state.config
        runtime = request.app.state.runtime
        tools = [t.name for t in runtime.tools.list_tools()]

        return {
            "name": config.name,
            "version": config.version,
            "description": config.description,
            "model": {
                "provider": config.agent.model.provider,
                "name": config.agent.model.name,
            },
            "tools": tools,
            "streaming": config.runtime.streaming,
        }

    @router.post("/v1/chat")
    async def chat(request: Request, body: ChatRequest) -> Any:
        """Send a message to the agent."""
        runtime = request.app.state.runtime
        session_id = body.session_id or str(uuid.uuid4())

        if body.stream:
            return EventSourceResponse(_stream_response(runtime, body.message, session_id))

        # Non-streaming response
        result = await runtime.handle(body.message, session_id)

        return ChatResponse(
            response=result.response,
            session_id=result.session_id,
            tool_calls=[
                ToolCallResponse(
                    tool=tc.tool, input=tc.input, output=tc.output, error=tc.error
                )
                for tc in result.tool_calls
            ],
            usage=UsageResponse(
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                total_tokens=result.usage.total_tokens,
            )
            if result.usage
            else None,
        )

    async def _stream_response(runtime: Any, message: str, session_id: str):
        """Generate SSE events for streaming."""
        import json

        async for chunk in runtime.stream(message, session_id):
            data = {"type": chunk.type}
            if chunk.content:
                data["content"] = chunk.content
            if chunk.tool:
                data["tool"] = chunk.tool
            if chunk.tool_output:
                data["tool_output"] = chunk.tool_output
            yield {"event": "message", "data": json.dumps(data)}

    return router
