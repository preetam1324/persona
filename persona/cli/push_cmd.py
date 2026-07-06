"""persona push — push built image to a Docker registry."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command("push")
@click.argument("image", required=False)
@click.option("--directory", "-d", default=None, help="Agent directory (default: current)")
def push_cmd(image: str | None, directory: str | None) -> None:
    """Push a built agent image to a Docker registry."""
    from pathlib import Path

    from persona.core.config import PersonaConfig

    agent_dir = Path(directory) if directory else Path.cwd()

    if not image:
        try:
            config = PersonaConfig.find_config(agent_dir)
            image = f"{config.name}:{config.version}"
        except FileNotFoundError:
            console.print("[red]Error:[/red] No image specified and no config.yaml found.")
            raise SystemExit(1)

    console.print(f"[bold]Pushing image:[/bold] {image}")

    try:
        import docker

        client = docker.from_env()
        result = client.images.push(image, stream=True, decode=True)

        for line in result:
            if "status" in line:
                layer = line.get("id", "")
                status = line["status"]
                if layer:
                    console.print(f"  [dim]{layer}: {status}[/dim]")
            if "error" in line:
                console.print(f"[red]Error:[/red] {line['error']}")
                raise SystemExit(1)

        console.print(f"\n[green]✓[/green] Pushed: [bold]{image}[/bold]\n")

    except Exception as e:
        console.print(f"\n[red]✗ Push failed:[/red] {e}")
        raise SystemExit(1)
