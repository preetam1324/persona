"""persona build — build a Docker image for the agent."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command("build")
@click.option("--directory", "-d", default=None, help="Agent directory (default: current)")
@click.option("--tag", "-t", default=None, help="Image tag (default: <name>:<version>)")
@click.option("--no-cache", is_flag=True, help="Build without cache")
def build_cmd(directory: str | None, tag: str | None, no_cache: bool) -> None:
    """Build a Docker image for the agent."""
    from pathlib import Path

    from persona.builder.image_builder import ImageBuilder
    from persona.core.config import PersonaConfig

    agent_dir = Path(directory) if directory else Path.cwd()

    try:
        config = PersonaConfig.find_config(agent_dir)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    image_tag = tag or f"{config.name}:{config.version}"

    console.print(f"[bold]Building image:[/bold] {image_tag}")
    console.print(f"[dim]Agent: {config.name} v{config.version}[/dim]")
    console.print(f"[dim]Python: {config.python_version}[/dim]")

    builder = ImageBuilder(config=config, agent_dir=agent_dir)

    try:
        image_id = builder.build(tag=image_tag, no_cache=no_cache)
        console.print(f"\n[green]✓[/green] Image built: [bold]{image_tag}[/bold]")
        console.print(f"[dim]  ID: {image_id[:12]}[/dim]")
        console.print(f"\n  docker run -p 8080:8080 -e OPENAI_API_KEY=sk-... {image_tag}\n")
    except Exception as e:
        console.print(f"\n[red]✗ Build failed:[/red] {e}")
        raise SystemExit(1)
