"""persona init — scaffold a new agent package."""

from __future__ import annotations

import shutil
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command("init")
@click.argument("name", default="my-agent")
@click.option("--directory", "-d", default=None, help="Parent directory (default: current)")
@click.option("--avatar", "with_avatar", is_flag=True, help="Include avatar configuration")
def init_cmd(name: str, directory: str | None, with_avatar: bool) -> None:
    """Scaffold a new agent package directory."""
    parent = Path(directory) if directory else Path.cwd()
    target = parent / name

    if target.exists():
        console.print(f"[red]Error:[/red] Directory '{name}' already exists.")
        raise SystemExit(1)

    # Copy template
    template_dir = Path(__file__).parent.parent / "templates" / "default"
    if template_dir.exists():
        shutil.copytree(template_dir, target)
    else:
        # Fallback: create minimal structure
        _create_minimal(target, name)

    # Replace placeholder in config.yaml
    config_path = target / "config.yaml"
    if config_path.exists():
        content = config_path.read_text()
        content = content.replace("my-agent", name)
        config_path.write_text(content)

    # Append avatar config if requested
    if with_avatar:
        _append_avatar_config(target / "config.yaml")

    console.print(f"\n[green]✓[/green] Created agent package: [bold]{name}/[/bold]")
    if with_avatar:
        console.print("  [cyan]Avatar enabled[/cyan] — includes voice + visual config")
    console.print(f"\n  cd {name}")
    console.print("  persona run        # Interactive chat")
    console.print("  persona serve      # Local HTTP server")
    if with_avatar:
        console.print("  persona avatar     # Launch avatar UI")
    console.print("  persona build      # Build Docker image\n")


def _create_minimal(target: Path, name: str) -> None:
    """Create a minimal agent structure when templates are missing."""
    target.mkdir(parents=True)
    (target / "agent").mkdir()
    (target / "tools").mkdir()
    (target / "data").mkdir()

    # config.yaml
    (target / "config.yaml").write_text(f"""name: {name}
version: "0.1.0"
description: "A helpful AI agent"

agent:
  system_prompt: |
    You are a helpful assistant. Answer questions clearly and concisely.
  model:
    provider: openai
    name: gpt-4o-mini
    parameters:
      temperature: 0.7
      max_tokens: 2048
  tools:
    - name: web_search
      type: builtin
    - name: code_executor
      type: builtin

runtime:
  concurrency: 4
  timeout_seconds: 120
  streaming: true

resources:
  cpu: "2"
  memory: "4Gi"

python_version: "3.11"
requirements_file: requirements.txt
secrets:
  - OPENAI_API_KEY
""")

    # requirements.txt
    (target / "requirements.txt").write_text("# Add your agent's Python dependencies here\n")

    # agent/agent.py
    (target / "agent" / "agent.py").write_text('''"""Custom agent logic (optional).

Override methods here only if you need behavior beyond what config.yaml provides.
For most agents, config.yaml alone is sufficient — no Python needed.
"""

from persona.core.agent import Agent


class MyAgent(Agent):
    def load(self):
        """Called once on startup. Load custom resources here."""
        pass
''')

    # .personaignore
    (target / ".personaignore").write_text("""# Files to exclude from Docker build context
__pycache__/
*.pyc
.git/
.env
.venv/
""")


def _append_avatar_config(config_path: Path) -> None:
    """Append avatar configuration block to config.yaml."""
    avatar_block = """
avatar:
  enabled: true
  appearance:
    type: sprite
    background: "#1a1a2e"
    idle_animation: breathing
  voice:
    provider: openai
    voice_id: alloy
    speed: 1.0
    language: en-US
  expressions:
    idle: neutral
    thinking: eyebrows_raised
    speaking: talking
    error: concerned
    happy: smile
  input:
    microphone: true
    stt_provider: browser
"""
    content = config_path.read_text()
    content += avatar_block
    config_path.write_text(content)
