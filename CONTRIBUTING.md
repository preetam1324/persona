# Contributing to Persona Framework

## Getting Started

```bash
git clone git@github.com:preetam1324/persona.git
cd persona
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -e ".[dev]"
```

## Project Structure

```
persona/           # Framework core
  core/            # Agent, config, provider, tool base classes
  runtime/         # AgentRuntime, memory, scheduler
  server/          # FastAPI endpoints
  providers/       # LLM providers (OpenAI, Anthropic, Ollama)
  tools/           # Built-in tools (web_search, code_executor, file_reader)
  storage/         # Async database layer (SQLAlchemy)
  cli/             # CLI commands (init, run, serve, build, push, validate)
  templates/       # Agent scaffolding template

linkedin-agent/    # LinkedIn lead generation agent
  agent/           # Custom LinkedInAgent subclass
  providers/       # LinkedIn API provider interface + implementations
  db/              # SQLAlchemy models + repository classes
  tools/           # 7 custom tools (search, export, message, etc.)
  tests/           # Unit test suite
  data/            # Message templates, exports
```

## Running Tests

### LinkedIn Agent (100 unit tests)

```bash
cd linkedin-agent
python -m pytest tests/ -v
```

No API keys, no PostgreSQL needed — tests use MockLinkedInProvider and SQLite in-memory.

### Validating an Agent

```bash
cd linkedin-agent   # or any agent directory
persona validate
```

## Creating a New Agent

```bash
persona init my-agent
cd my-agent
# Edit config.yaml, add tools in tools/, customize agent in agent/
persona validate
persona run          # Interactive CLI
persona serve        # HTTP server
```

## Adding a Custom Tool

1. Create `tools/my_tool.py`:

```python
from persona.core.tool import Tool, ToolResult

class MyTool(Tool):
    name = "my_tool"
    description = "What this tool does"
    parameters = {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "Input value"},
        },
        "required": ["input"],
    }

    async def execute(self, **kwargs) -> ToolResult:
        value = kwargs["input"]
        return ToolResult(output=f"Processed: {value}")
```

2. Register in `config.yaml`:

```yaml
tools:
  - name: my_tool
    type: custom
    module: tools.my_tool
    class: MyTool
```

## Adding a New LLM Provider

1. Subclass `LLMProvider` in `persona/providers/`
2. Implement `complete()` and `stream()` methods
3. Register with `ProviderRegistry.register("name", MyProvider)` at module level
4. Import in `persona/providers/registry.py`

## Code Style

- Python 3.11+, type hints throughout
- `async`/`await` for all I/O operations
- Pydantic v2 for config validation
- Tools return `ToolResult(output=...)` on success, `ToolResult(error="...")` on failure
- Keep tools stateless — inject dependencies via attributes, not constructors

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new LinkedIn search filter
fix: validate_cmd Path concatenation
test: add campaign lifecycle integration tests
chore: remove __pycache__ from tracking
docs: update contributing guide
```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Run `persona validate` on any modified agents
4. Run `python -m pytest` to verify all tests pass
5. Open a PR with a clear description of changes
