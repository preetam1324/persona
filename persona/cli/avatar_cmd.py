"""persona avatar — launch the avatar UI locally."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command("avatar")
@click.option("--directory", "-d", default=None, help="Agent directory (default: current)")
@click.option("--host", default="127.0.0.1", help="Host to bind")
@click.option("--port", "-p", default=8000, type=int, help="Port to serve on")
def avatar_cmd(directory: str | None, host: str, port: int) -> None:
    """Launch the agent with avatar UI in the browser."""
    import os
    import webbrowser
    from pathlib import Path

    agent_dir = Path(directory) if directory else Path.cwd()
    os.environ["PERSONA_AGENT_DIR"] = str(agent_dir)

    from persona.core.config import PersonaConfig

    config = PersonaConfig.find_config(agent_dir)

    if not config.avatar or not config.avatar.enabled:
        console.print(
            "[yellow]Warning:[/yellow] Avatar is not enabled in config.yaml. "
            "Add 'avatar:\\n  enabled: true' to your config.yaml."
        )
        console.print("Starting server anyway (avatar endpoints will report disabled).\n")

    console.print(f"[bold]Persona Avatar[/bold] — {config.name}")
    console.print(f"  Avatar UI: [link]http://{host}:{port}/avatar[/link]")
    console.print(f"  API docs:  [link]http://{host}:{port}/docs[/link]")
    console.print(f"\n  Press Ctrl+C to stop.\n")

    # Open browser
    webbrowser.open(f"http://{host}:{port}/avatar")

    import uvicorn

    uvicorn.run(
        "persona.server.app:create_app",
        host=host,
        port=port,
        factory=True,
        log_level="info",
    )
