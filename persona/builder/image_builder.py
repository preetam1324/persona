"""ImageBuilder — orchestrates Docker build context and image creation."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from jinja2 import Template

from persona.core.config import PersonaConfig


class ImageBuilder:
    """Builds Docker images from Persona agent packages."""

    def __init__(self, config: PersonaConfig, agent_dir: Path):
        self.config = config
        self.agent_dir = agent_dir.resolve()

    def build(self, tag: str, no_cache: bool = False) -> str:
        """Build a Docker image and return the image ID."""
        import docker

        client = docker.from_env()

        # Assemble build context
        with tempfile.TemporaryDirectory() as tmp:
            context_dir = Path(tmp)
            self._assemble_context(context_dir)

            # Build
            image, logs = client.images.build(
                path=str(context_dir),
                tag=tag,
                nocache=no_cache,
                rm=True,
            )

            return image.id

    def _assemble_context(self, context_dir: Path) -> None:
        """Assemble the Docker build context directory."""
        app_dir = context_dir / "app"
        app_dir.mkdir()

        # Copy agent files (respecting .personaignore)
        ignore_patterns = self._load_ignore_patterns()

        for item in self.agent_dir.iterdir():
            if item.name.startswith(".") and item.name != ".personaignore":
                continue
            if any(item.match(p) for p in ignore_patterns):
                continue

            dest = app_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, ignore=shutil.ignore_patterns(*ignore_patterns))
            else:
                shutil.copy2(item, dest)

        # Generate Dockerfile
        dockerfile_content = self._render_dockerfile()
        (context_dir / "Dockerfile").write_text(dockerfile_content)

        # Generate server requirements (framework deps)
        self._write_server_requirements(context_dir)

    def _render_dockerfile(self) -> str:
        """Render the Dockerfile from template."""
        template_path = Path(__file__).parent / "templates" / "Dockerfile.jinja"
        if template_path.exists():
            template = Template(template_path.read_text())
        else:
            template = Template(DEFAULT_DOCKERFILE_TEMPLATE)

        return template.render(
            python_version=self.config.python_version,
            system_packages=self.config.system_packages,
            requirements_file=self.config.requirements_file,
            port=8080,
        )

    def _write_server_requirements(self, context_dir: Path) -> None:
        """Write the framework's own requirements for the container."""
        reqs = [
            "persona",
            "pydantic>=2.0",
            "pyyaml>=6.0",
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.20.0",
            "httpx>=0.24",
            "openai>=1.0",
            "anthropic>=0.20",
            "sse-starlette>=1.6",
            "click>=8.0",
            "rich>=13.0",
            "jinja2>=3.1",
        ]
        (context_dir / "server-requirements.txt").write_text("\n".join(reqs) + "\n")

    def _load_ignore_patterns(self) -> list[str]:
        """Load patterns from .personaignore."""
        ignore_file = self.agent_dir / ".personaignore"
        default_patterns = [
            "__pycache__",
            "*.pyc",
            ".git",
            ".env",
            ".venv",
            "venv",
            ".personaignore",
        ]

        if not ignore_file.exists():
            return default_patterns

        patterns = []
        for line in ignore_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line.rstrip("/"))

        return patterns or default_patterns


DEFAULT_DOCKERFILE_TEMPLATE = """\
FROM python:{{ python_version }}-slim

# System packages
{% if system_packages %}
RUN apt-get update && apt-get install -y --no-install-recommends \\
    {{ system_packages | join(' ') }} \\
    && rm -rf /var/lib/apt/lists/*
{% endif %}

# Create non-root user
RUN useradd -m -s /bin/bash persona
WORKDIR /app

# Install framework (server) dependencies
COPY server-requirements.txt /tmp/server-requirements.txt
RUN pip install --no-cache-dir -r /tmp/server-requirements.txt

# Install agent dependencies
COPY app/{{ requirements_file }} /app/{{ requirements_file }}
RUN pip install --no-cache-dir -r /app/{{ requirements_file }} 2>/dev/null || true

# Copy agent code
COPY app/ /app/

# Set environment
ENV PERSONA_AGENT_DIR=/app
ENV PERSONA_PORT={{ port }}

# Switch to non-root
USER persona

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{{ port }}/health')"

EXPOSE {{ port }}

CMD ["python", "-m", "persona.server.main"]
"""
