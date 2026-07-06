"""FastAPI application factory."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from persona.core.config import PersonaConfig
from persona.runtime.agent_runtime import AgentRuntime


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Persona Agent Server",
        version="0.1.0",
        docs_url="/docs",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load agent
    agent_dir = os.environ.get("PERSONA_AGENT_DIR", "/app")
    sys.path.insert(0, agent_dir)

    config = PersonaConfig.find_config(agent_dir)

    # Gather secrets from environment
    secrets = {}
    missing_secrets = []
    for key in config.secrets:
        val = os.environ.get(key)
        if val:
            secrets[key] = val
        else:
            missing_secrets.append(key)

    if missing_secrets:
        import logging

        logging.warning(f"Missing secrets: {', '.join(missing_secrets)}")

    # Build runtime
    runtime = AgentRuntime.from_config(config, secrets)

    # Store on app state
    app.state.config = config
    app.state.runtime = runtime
    app.state.ready = True

    # Register routes
    from persona.server.endpoints import create_router

    app.include_router(create_router())

    # Conditionally register avatar routes
    if config.avatar and config.avatar.enabled:
        from persona.server.avatar_endpoints import create_avatar_router

        app.include_router(create_avatar_router())

        # Serve avatar frontend at /avatar
        from fastapi.staticfiles import StaticFiles

        frontend_dir = Path(__file__).parent.parent / "avatar" / "frontend"
        if frontend_dir.exists():
            app.mount("/avatar", StaticFiles(directory=str(frontend_dir), html=True), name="avatar-ui")

    return app
