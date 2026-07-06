"""persona serve — local HTTP development server."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command("serve")
@click.option("--directory", "-d", default=None, help="Agent directory (default: current)")
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", "-p", default=8080, type=int, help="Bind port")
@click.option("--reload", is_flag=True, help="Auto-reload on file changes")
def serve_cmd(directory: str | None, host: str, port: int, reload: bool) -> None:
    """Start a local HTTP server for the agent."""
    import os
    import sys

    # Set the agent directory so the server can find config.yaml
    agent_dir = directory or os.getcwd()
    os.environ["PERSONA_AGENT_DIR"] = agent_dir

    # Add agent directory to path for custom tools
    sys.path.insert(0, agent_dir)

    console.print(f"[bold green]Persona[/bold green] serving agent from: {agent_dir}")
    console.print(f"[dim]Endpoints:[/dim]")
    console.print(f"  POST http://{host}:{port}/v1/chat")
    console.print(f"  GET  http://{host}:{port}/health")
    console.print(f"  GET  http://{host}:{port}/ready")
    console.print(f"  GET  http://{host}:{port}/v1/agent/info")
    console.print()

    import uvicorn

    uvicorn.run(
        "persona.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
