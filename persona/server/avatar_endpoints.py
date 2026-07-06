"""Avatar endpoints — HTTP + WebSocket for real-time avatar interaction."""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from persona.avatar.tts import TTSProviderRegistry


class AvatarChatRequest(BaseModel):
    """Request body for avatar chat endpoint."""

    message: str
    conversation_id: str | None = None


def create_avatar_router() -> APIRouter:
    """Create router for avatar-specific endpoints."""
    router = APIRouter(prefix="/v1/avatar", tags=["avatar"])

    @router.post("/chat")
    async def avatar_chat(req: AvatarChatRequest, request: Request):
        """Chat with avatar — returns text + audio + visemes."""
        runtime = request.app.state.runtime
        config = request.app.state.config

        # Get agent response text
        session_id = req.conversation_id or "avatar-default"
        response = await runtime.handle(req.message, session_id)
        text = response.response

        # Synthesize audio if avatar is enabled
        avatar_cfg = config.avatar
        audio_data = None
        visemes = []

        if avatar_cfg and avatar_cfg.enabled:
            tts = TTSProviderRegistry.get(
                avatar_cfg.voice.provider,
                voice_id=avatar_cfg.voice.voice_id,
                speed=avatar_cfg.voice.speed,
            )
            chunk = await tts.synthesize(text)
            audio_data = base64.b64encode(chunk.audio).decode("ascii")
            visemes = [
                {"id": v.id, "start_ms": v.start_ms, "duration_ms": v.duration_ms}
                for v in chunk.visemes
            ]

        return JSONResponse(
            {
                "text": text,
                "audio": audio_data,
                "audio_format": "mp3" if audio_data else None,
                "visemes": visemes,
                "expression": "speaking" if audio_data else "idle",
                "conversation_id": req.conversation_id,
            }
        )

    @router.websocket("/stream")
    async def avatar_stream(websocket: WebSocket):
        """WebSocket for real-time avatar chat with streaming audio."""
        await websocket.accept()
        runtime = websocket.app.state.runtime
        config = websocket.app.state.config
        avatar_cfg = config.avatar

        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                user_text = msg.get("message", "")
                conversation_id = msg.get("conversation_id")

                if not user_text:
                    await websocket.send_json({"error": "Empty message"})
                    continue

                # Send thinking state
                await websocket.send_json({"type": "state", "expression": "thinking"})

                # Get agent response
                session_id = conversation_id or "avatar-default"
                response = await runtime.handle(user_text, session_id)
                text = response.response

                # Send text response
                await websocket.send_json({"type": "text", "content": text})

                # Stream audio if avatar is enabled
                if avatar_cfg and avatar_cfg.enabled:
                    tts = TTSProviderRegistry.get(
                        avatar_cfg.voice.provider,
                        voice_id=avatar_cfg.voice.voice_id,
                        speed=avatar_cfg.voice.speed,
                    )
                    async for chunk in tts.stream(text):
                        audio_b64 = base64.b64encode(chunk.audio).decode("ascii")
                        await websocket.send_json(
                            {
                                "type": "audio",
                                "audio": audio_b64,
                                "format": chunk.format,
                                "sample_rate": chunk.sample_rate,
                                "visemes": [
                                    {
                                        "id": v.id,
                                        "start_ms": v.start_ms,
                                        "duration_ms": v.duration_ms,
                                    }
                                    for v in chunk.visemes
                                ],
                                "is_final": chunk.is_final,
                            }
                        )

                # Send done
                await websocket.send_json({"type": "done", "expression": "idle"})

        except WebSocketDisconnect:
            pass

    @router.get("/info")
    async def avatar_info(request: Request):
        """Return avatar configuration metadata."""
        config = request.app.state.config
        avatar_cfg = config.avatar

        if not avatar_cfg or not avatar_cfg.enabled:
            return JSONResponse({"enabled": False})

        return JSONResponse(
            {
                "enabled": True,
                "appearance": avatar_cfg.appearance.model_dump(),
                "voice": {
                    "provider": avatar_cfg.voice.provider,
                    "voice_id": avatar_cfg.voice.voice_id,
                },
                "expressions": avatar_cfg.expressions.model_dump(),
                "input": avatar_cfg.input.model_dump(),
            }
        )

    return router
