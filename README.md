# Persona

**Define AI agents in YAML, deploy anywhere as Docker containers.**

Persona is a free, open-source Python framework inspired by Baseten's Truss. Where Truss packages ML models, Persona packages **agentic AI** — agents that reason, use tools, and answer questions.

## Quickstart

```bash
pip install persona
persona init my-agent
cd my-agent
# Edit config.yaml with your system prompt and tools
persona run          # Interactive chat
persona serve        # Local HTTP server
persona build        # Build Docker image
```

## License

Apache-2.0
