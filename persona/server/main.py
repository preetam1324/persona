"""Server entry point — used as Docker CMD."""

import os
import sys

import uvicorn


def main() -> None:
    """Run the Persona server (called by Docker CMD)."""
    agent_dir = os.environ.get("PERSONA_AGENT_DIR", "/app")
    sys.path.insert(0, agent_dir)

    host = os.environ.get("PERSONA_HOST", "0.0.0.0")
    port = int(os.environ.get("PERSONA_PORT", "8080"))
    workers = int(os.environ.get("PERSONA_WORKERS", "1"))

    uvicorn.run(
        "persona.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        workers=workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
