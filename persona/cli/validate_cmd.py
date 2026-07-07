"""persona validate — validate agent config and structure."""

from __future__ import annotations

import click
from rich.console import Console

console = Console()


@click.command("validate")
@click.option("--directory", "-d", default=None, help="Agent directory (default: current)")
def validate_cmd(directory: str | None) -> None:
    """Validate the agent's config.yaml and directory structure."""
    from pathlib import Path

    from persona.core.config import PersonaConfig

    agent_dir = Path(directory) if directory else Path.cwd()
    errors: list[str] = []
    warnings: list[str] = []

    # Check config.yaml exists
    config_path = agent_dir / "config.yaml"
    if not config_path.exists():
        console.print(f"[red]✗[/red] No config.yaml found in {agent_dir}")
        raise SystemExit(1)

    # Parse and validate config
    try:
        config = PersonaConfig.from_yaml(config_path)
        console.print(f"[green]✓[/green] config.yaml is valid")
    except Exception as e:
        console.print(f"[red]✗[/red] config.yaml validation failed: {e}")
        raise SystemExit(1)

    # Check agent class file if specified
    if config.agent.class_file:
        class_path = agent_dir / config.agent.class_file
        if not class_path.exists():
            errors.append(f"Agent class file not found: {config.agent.class_file}")
        else:
            console.print(f"[green]✓[/green] Agent class file exists: {config.agent.class_file}")

    # Check requirements file
    req_path = agent_dir / config.requirements_file
    if req_path.exists():
        console.print(f"[green]✓[/green] Requirements file exists: {config.requirements_file}")
    else:
        warnings.append(f"Requirements file not found: {config.requirements_file}")

    # Check custom tool modules
    for tool_ref in config.agent.tools:
        if tool_ref.type == "custom":
            if not tool_ref.module:
                errors.append(f"Custom tool '{tool_ref.name}' has no module specified")
            else:
                # Check if the module file exists (convert dotted path to file path)
                module_parts = tool_ref.module.split(".")
                possible_path = agent_dir / ("/".join(module_parts) + ".py")
                # Also check with __init__.py
                if possible_path.exists():
                    console.print(f"[green]✓[/green] Custom tool module: {tool_ref.module}")
                else:
                    warnings.append(
                        f"Custom tool module '{tool_ref.module}' — file not found at {possible_path} "
                        f"(may still work if installed as a package)"
                    )

    # Check data directory for RAG
    if config.agent.retrieval.enabled:
        data_dir = agent_dir / config.agent.retrieval.data_dir
        if data_dir.exists() and any(data_dir.iterdir()):
            console.print(f"[green]✓[/green] RAG data directory has files")
        else:
            warnings.append(f"RAG enabled but data directory is empty: {config.agent.retrieval.data_dir}")

    # Check provider is known
    from persona.core.provider import ProviderRegistry
    import persona.providers.registry  # noqa: F401

    if ProviderRegistry.get(config.agent.model.provider):
        console.print(f"[green]✓[/green] Provider '{config.agent.model.provider}' is registered")
    else:
        errors.append(f"Unknown provider: '{config.agent.model.provider}'")

    # Check builtin tools are valid
    from persona.tools.registry import BUILTIN_TOOLS

    for tool_ref in config.agent.tools:
        if tool_ref.type == "builtin":
            if tool_ref.name in BUILTIN_TOOLS:
                console.print(f"[green]✓[/green] Builtin tool: {tool_ref.name}")
            else:
                errors.append(f"Unknown builtin tool: '{tool_ref.name}'")

    # Report
    console.print()
    if warnings:
        for w in warnings:
            console.print(f"[yellow]⚠[/yellow] {w}")
    if errors:
        for e in errors:
            console.print(f"[red]✗[/red] {e}")
        console.print(f"\n[red]Validation failed with {len(errors)} error(s).[/red]")
        raise SystemExit(1)
    else:
        console.print(f"[green]✓ Agent '{config.name}' is valid and ready.[/green]")
