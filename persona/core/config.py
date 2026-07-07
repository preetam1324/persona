"""PersonaConfig — Pydantic v2 model for config.yaml validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """LLM model configuration."""

    provider: str = "openai"
    name: str = "gpt-4o-mini"
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolRef(BaseModel):
    """Reference to a tool (builtin or custom)."""

    name: str
    type: str = "builtin"  # "builtin" or "custom"
    module: str | None = None
    class_name: str | None = Field(None, alias="class")
    config: dict[str, Any] = Field(default_factory=dict)


class EmbeddingsConfig(BaseModel):
    """Embeddings model for RAG."""

    provider: str = "openai"
    model: str = "text-embedding-3-small"


class RetrievalConfig(BaseModel):
    """RAG retrieval configuration."""

    enabled: bool = False
    data_dir: str = "data/"
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)


class OrchestrationConfig(BaseModel):
    """Multi-agent orchestration (Phase 1: single only)."""

    mode: str = "single"  # "single", "router", "sequential", "parallel"
    sub_agents: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Agent behavior configuration."""

    class_file: str | None = None
    class_name: str = "Agent"
    system_prompt: str = "You are a helpful assistant."
    model: ModelConfig = Field(default_factory=ModelConfig)
    tools: list[ToolRef] = Field(default_factory=list)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)


class DatabaseConfig(BaseModel):
    """Database configuration for persistent storage."""

    url: str = ""  # e.g. "postgresql+asyncpg://user:pass@host/db"


class SchedulerConfig(BaseModel):
    """In-process job scheduler configuration."""

    enabled: bool = False


class RuntimeConfig(BaseModel):
    """Runtime / serving configuration."""

    concurrency: int = 4
    timeout_seconds: int = 300
    streaming: bool = True
    max_turns: int = 10  # Max tool-call loops before forcing a response
    database: DatabaseConfig | None = None
    scheduler: SchedulerConfig | None = None


class ResourceConfig(BaseModel):
    """Infrastructure resource requirements."""

    cpu: str = "2"
    memory: str = "4Gi"
    gpu: str | None = None


# --- Avatar configuration (Phase 2) ---


class AvatarAppearanceConfig(BaseModel):
    """Visual appearance of the avatar."""

    type: Literal["sprite", "3d"] = "sprite"
    asset: str = "assets/default.png"
    background: str = "#1a1a2e"
    size: list[int] = Field(default_factory=lambda: [512, 512])
    idle_animation: str = "breathing"


class AvatarVoiceConfig(BaseModel):
    """Text-to-speech voice configuration."""

    provider: Literal["openai", "azure", "elevenlabs"] = "openai"
    voice_id: str = "alloy"
    speed: float = 1.0
    language: str = "en-US"


class AvatarExpressionsConfig(BaseModel):
    """Facial expression mapping."""

    idle: str = "neutral"
    thinking: str = "eyebrows_raised"
    speaking: str = "talking"
    error: str = "concerned"
    happy: str = "smile"


class AvatarInputConfig(BaseModel):
    """Voice input configuration."""

    microphone: bool = False
    stt_provider: Literal["browser", "openai", "azure"] = "browser"


class AvatarConfig(BaseModel):
    """Avatar (visual skin + voice) configuration — fully optional."""

    enabled: bool = False
    appearance: AvatarAppearanceConfig = Field(default_factory=AvatarAppearanceConfig)
    voice: AvatarVoiceConfig = Field(default_factory=AvatarVoiceConfig)
    expressions: AvatarExpressionsConfig = Field(default_factory=AvatarExpressionsConfig)
    input: AvatarInputConfig = Field(default_factory=AvatarInputConfig)


class PersonaConfig(BaseModel):
    """Root configuration model — validates config.yaml."""

    name: str = "my-agent"
    version: str = "0.1.0"
    description: str = ""
    agent: AgentConfig = Field(default_factory=AgentConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)
    avatar: AvatarConfig | None = None
    python_version: str = "3.11"
    requirements_file: str = "requirements.txt"
    system_packages: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)
    environment_variables: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PersonaConfig":
        """Load and validate config from a YAML file."""
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data or {})

    @classmethod
    def find_config(cls, directory: str | Path | None = None) -> "PersonaConfig":
        """Find and load config.yaml from the given or current directory."""
        directory = Path(directory) if directory else Path.cwd()
        config_path = directory / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"No config.yaml found in {directory}")
        return cls.from_yaml(config_path)
