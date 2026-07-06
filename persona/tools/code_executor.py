"""Code executor tool — runs Python code in a sandboxed subprocess."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from persona.core.tool import Tool, ToolResult


class CodeExecutorTool(Tool):
    """Execute Python code in an isolated subprocess."""

    name = "code_executor"
    description = (
        "Execute Python code and return the output. "
        "Use for calculations, data processing, or generating results programmatically."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Max execution time in seconds (default 30)",
                "default": 30,
            },
        },
        "required": ["code"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        code = kwargs.get("code", "")
        timeout = min(kwargs.get("timeout", 30), 60)  # Cap at 60s

        if not code.strip():
            return ToolResult(output="", error="No code provided")

        # Write code to a temp file and execute in subprocess
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write(code)
            script_path = Path(f.name)

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={"PATH": "", "HOME": tempfile.gettempdir()},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(output="", error=f"Execution timed out after {timeout}s")

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                return ToolResult(output=output, error=errors or f"Exit code: {proc.returncode}")

            combined = output
            if errors:
                combined += f"\n[stderr]: {errors}"

            return ToolResult(output=combined)

        finally:
            script_path.unlink(missing_ok=True)
