"""CLI entry point — persona command group."""

from __future__ import annotations

import click

from persona import __version__


@click.group()
@click.version_option(version=__version__, prog_name="persona")
def cli() -> None:
    """Persona — Define AI agents in YAML, deploy anywhere as Docker containers."""
    pass


# Import and register subcommands
from persona.cli.init_cmd import init_cmd  # noqa: E402
from persona.cli.run_cmd import run_cmd  # noqa: E402
from persona.cli.serve_cmd import serve_cmd  # noqa: E402
from persona.cli.build_cmd import build_cmd  # noqa: E402
from persona.cli.push_cmd import push_cmd  # noqa: E402
from persona.cli.validate_cmd import validate_cmd  # noqa: E402
from persona.cli.avatar_cmd import avatar_cmd  # noqa: E402

cli.add_command(init_cmd, "init")
cli.add_command(run_cmd, "run")
cli.add_command(serve_cmd, "serve")
cli.add_command(build_cmd, "build")
cli.add_command(push_cmd, "push")
cli.add_command(validate_cmd, "validate")
cli.add_command(avatar_cmd, "avatar")
