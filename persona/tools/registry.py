"""Tool registry — discovers and instantiates tools from config."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from persona.core.config import ToolRef
from persona.core.tool import Tool, ToolRegistry
from persona.tools.code_executor import CodeExecutorTool
from persona.tools.file_reader import FileReaderTool
from persona.tools.web_search import WebSearchTool

# Map of builtin tool names to their classes
BUILTIN_TOOLS: dict[str, type[Tool]] = {
    "web_search": WebSearchTool,
    "code_executor": CodeExecutorTool,
    "file_reader": FileReaderTool,
}


def build_tool_registry(
    tool_refs: list[ToolRef],
    data_dir: Path | None = None,
) -> ToolRegistry:
    """Build a ToolRegistry from config tool references."""
    registry = ToolRegistry()

    for ref in tool_refs:
        if ref.type == "builtin":
            tool_class = BUILTIN_TOOLS.get(ref.name)
            if tool_class is None:
                available = ", ".join(BUILTIN_TOOLS.keys())
                raise ValueError(
                    f"Unknown builtin tool '{ref.name}'. Available: {available}"
                )
            # Special handling for file_reader (needs data_dir)
            if ref.name == "file_reader" and data_dir:
                tool = tool_class(data_dir=data_dir)  # type: ignore
            else:
                tool = tool_class()
            registry.register(tool)

        elif ref.type == "custom":
            if not ref.module:
                raise ValueError(f"Custom tool '{ref.name}' must specify 'module'")
            class_name = ref.class_name or ref.name.title().replace("_", "")
            tool = _load_custom_tool(ref.module, class_name)
            registry.register(tool)

    return registry


def _load_custom_tool(module_path: str, class_name: str) -> Tool:
    """Dynamically load a custom tool class."""
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise ValueError(f"Cannot import tool module '{module_path}': {e}") from e

    tool_class = getattr(module, class_name, None)
    if tool_class is None:
        raise ValueError(f"Class '{class_name}' not found in module '{module_path}'")

    if not isinstance(tool_class, type) or not issubclass(tool_class, Tool):
        raise ValueError(f"'{class_name}' must be a subclass of persona.core.tool.Tool")

    return tool_class()
