"""Provider registry — imports all providers to register them."""

try:
    from persona.providers.openai_provider import OpenAIProvider  # noqa: F401
except ImportError:
    pass

try:
    from persona.providers.anthropic_provider import AnthropicProvider  # noqa: F401
except ImportError:
    pass

try:
    from persona.providers.ollama_provider import OllamaProvider  # noqa: F401
except ImportError:
    pass
