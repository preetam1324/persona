"""persona run — interactive CLI chat with the agent."""

from __future__ import annotations

import asyncio
import os
import uuid

import click
from rich.console import Console
from rich.markdown import Markdown

console = Console()


@click.command("run")
@click.option("--directory", "-d", default=None, help="Agent directory (default: current)")
def run_cmd(directory: str | None) -> None:
    """Interactive CLI chat with the agent (local, no server)."""
    asyncio.run(_run(directory))


async def _run(directory: str | None) -> None:
    from persona.core.config import PersonaConfig
    from persona.runtime.agent_runtime import AgentRuntime

    # Load config
    try:
        config = PersonaConfig.find_config(directory)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        console.print("Run 'persona init' to create an agent, or use -d to specify a directory.")
        raise SystemExit(1)

    # Gather secrets from environment
    secrets = {}
    for key in config.secrets:
        val = os.environ.get(key)
        if not val:
            console.print(f"[yellow]Warning:[/yellow] Secret '{key}' not set in environment.")
        else:
            secrets[key] = val

    # Build runtime
    console.print(f"[dim]Loading agent: {config.name} (v{config.version})[/dim]")
    console.print(f"[dim]Model: {config.agent.model.provider}/{config.agent.model.name}[/dim]")

    try:
        runtime = AgentRuntime.from_config(config, secrets)
    except Exception as e:
        console.print(f"[red]Error loading agent:[/red] {e}")
        raise SystemExit(1)

    tools = runtime.tools.list_tools()
    if tools:
        tool_names = ", ".join(t.name for t in tools)
        console.print(f"[dim]Tools: {tool_names}[/dim]")

    console.print(f"\n[bold green]{config.name}[/bold green] is ready. Type your message (Ctrl+C to exit).\n")

    session_id = str(uuid.uuid4())

    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input.strip():
            continue

        if user_input.strip().lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.strip().lower() == "/clear":
            runtime.memory.clear_session(session_id)
            session_id = str(uuid.uuid4())
            console.print("[dim]Conversation cleared.[/dim]\n")
            continue

        # Stream response
        console.print(f"\n[bold green]{config.name}:[/bold green] ", end="")

        try:
            if config.runtime.streaming:
                full_response = ""
                async for chunk in runtime.stream(user_input, session_id):
                    if chunk.type == "token" and chunk.content:
                        console.print(chunk.content, end="", highlight=False)
                        full_response += chunk.content
                    elif chunk.type == "tool_call":
                        console.print(f"\n[dim]  ⚡ Using tool: {chunk.tool}[/dim]", end="")
                    elif chunk.type == "tool_result":
                        console.print(f" [dim]✓[/dim]", end="")
                    elif chunk.type == "done":
                        pass
                console.print()  # newline after streaming
            else:
                response = await runtime.handle(user_input, session_id)
                console.print(Markdown(response.response))
                if response.tool_calls:
                    for tc in response.tool_calls:
                        status = "✓" if not tc.error else f"✗ {tc.error}"
                        console.print(f"  [dim]⚡ {tc.tool}: {status}[/dim]")
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")

        console.print()
