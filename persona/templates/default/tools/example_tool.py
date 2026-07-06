"""Example custom tool.

To use this tool, add it to your config.yaml:

  tools:
    - name: example_tool
      type: custom
      module: tools.example_tool
      class: ExampleTool
"""

from typing import Any

from persona.core.tool import Tool, ToolResult


class ExampleTool(Tool):
    name = "example_tool"
    description = "An example custom tool — replace with your own logic"
    parameters = {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": "Text to process",
            },
        },
        "required": ["input_text"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        input_text = kwargs.get("input_text", "")
        # Replace with your tool logic
        result = f"Processed: {input_text}"
        return ToolResult(output=result)
