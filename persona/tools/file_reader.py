"""File reader tool — reads files from the agent's data directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from persona.core.tool import Tool, ToolResult


class FileReaderTool(Tool):
    """Read files from the agent's bundled data directory."""

    name = "file_reader"
    description = "Read a file from the agent's data directory. Use to look up bundled information."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file within the data directory",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to read (default: all)",
            },
        },
        "required": ["path"],
    }

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or Path("data")

    async def execute(self, **kwargs: Any) -> ToolResult:
        rel_path = kwargs.get("path", "")
        max_lines = kwargs.get("max_lines")

        if not rel_path:
            return ToolResult(output="", error="No path provided")

        # Prevent path traversal
        target = (self._data_dir / rel_path).resolve()
        if not str(target).startswith(str(self._data_dir.resolve())):
            return ToolResult(output="", error="Access denied: path outside data directory")

        if not target.exists():
            return ToolResult(output="", error=f"File not found: {rel_path}")

        if not target.is_file():
            return ToolResult(output="", error=f"Not a file: {rel_path}")

        try:
            content = target.read_text(encoding="utf-8")
            if max_lines:
                lines = content.splitlines()[:max_lines]
                content = "\n".join(lines)
            return ToolResult(output=content)
        except Exception as e:
            return ToolResult(output="", error=f"Error reading file: {e}")
