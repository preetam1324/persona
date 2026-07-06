# AI Avatar Architecture — Phase 2

## Overview

The Avatar capability adds a **visual + voice presentation layer** on top of existing Persona agents. It is fully optional — existing text-only agents continue to work unchanged. A developer opts in by adding an `avatar:` section to their `config.yaml`.

```
+-----------------------------------------------------------------------+
|                         PERSONA FRAMEWORK                             |
|                                                                       |
|  +----------------------------------------------------------------+  |
|  |                    EXISTING (Phase 1)                           |  |
|  |                                                                 |  |
|  |  config.yaml --> AgentRuntime --> LLM Provider --> Text Response |  |
|  |                       |                                         |  |
|  |                       +---> Tools (web_search, code_exec, etc.) |  |
|  |                       +---> Memory (conversation history)       |  |
|  +----------------------------------------------------------------+  |
|                              |                                        |
|                              | stream() output                        |
|                              v                                        |
|  +----------------------------------------------------------------+  |
|  |                    NEW (Phase 2 - Avatar Layer)                 |  |
|  |                                                                 |  |
|  |  Text Chunks --> TTS Provider --> Audio Stream + Viseme Timeline |  |
|  |                                         |                       |  |
|  |                                         v                       |  |
|  |                              WebSocket / SSE Endpoint           |  |
|  |                                         |                       |  |
|  |                                         v                       |  |
|  |                              Web Frontend (Three.js/PixiJS)     |  |
|  |                              +-- 3D/2D Character Renderer       |  |
|  |                              +-- Lip-sync Engine (visemes)      |  |
|  |                              +-- Expression System              |  |
|  |                              +-- Audio Playback                 |  |
|  +----------------------------------------------------------------+  |
+-----------------------------------------------------------------------+
```

## Design Principles

1. **Additive, not invasive** — Zero changes to AgentRuntime, providers, tools, or memory
2. **Opt-in via config** — No `avatar:` section = text-only agent (backward compatible)
3. **Provider-agnostic TTS** — Swap between OpenAI, Azure Speech, ElevenLabs via config
4. **Ship in container** — Frontend, TTS pipeline, and avatar assets all package into the same Docker image
5. **Works locally** — `persona avatar` opens a browser to a local dev server

---

## Config Extension

The `avatar` section is added as an optional top-level field in `config.yaml`:

```yaml
name: my-avatar-agent
version: "0.1.0"
description: "A customer support agent with visual avatar"

# --- Existing agent config (unchanged) ---
agent:
  system_prompt: |
    You are a friendly customer support representative named Alex.
  model:
    provider: openai
    name: gpt-4o-mini
    parameters:
      temperature: 0.7
  tools:
    - name: web_search
      type: builtin

runtime:
  streaming: true
  max_turns: 10

# --- NEW: Avatar config (optional) ---
avatar:
  enabled: true

  appearance:
    type: sprite # "sprite" (2D) or "3d" (glTF/GLB model)
    asset: "assets/alex.png" # Sprite sheet or 3D model path
    background: "#1a1a2e" # Background color/image
    size: [512, 512] # Canvas size [width, height]
    idle_animation: "breathing"

  voice:
    provider: openai # "openai" | "azure" | "elevenlabs"
    voice_id: "alloy" # Provider-specific voice identifier
    speed: 1.0 # Playback speed multiplier
    language: "en-US" # BCP-47 language tag

  expressions:
    idle: "neutral"
    thinking: "eyebrows_raised"
    speaking: "talking"
    error: "concerned"
    happy: "smile"

  input:
    microphone: true # Enable speech-to-text input
    stt_provider: browser # "browser" (Web Speech API) | "openai" | "azure"

secrets:
  - OPENAI_API_KEY
```

### Pydantic Models

```python
# persona/core/config.py - new models

class AvatarAppearanceConfig(BaseModel):
    type: Literal["sprite", "3d"] = "sprite"
    asset: str = "assets/default.png"
    background: str = "#1a1a2e"
    size: tuple[int, int] = (512, 512)
    idle_animation: str = "breathing"

class AvatarVoiceConfig(BaseModel):
    provider: Literal["openai", "azure", "elevenlabs"] = "openai"
    voice_id: str = "alloy"
    speed: float = 1.0
    language: str = "en-US"

class AvatarExpressionsConfig(BaseModel):
    idle: str = "neutral"
    thinking: str = "eyebrows_raised"
    speaking: str = "talking"
    error: str = "concerned"
    happy: str = "smile"

class AvatarInputConfig(BaseModel):
    microphone: bool = False
    stt_provider: Literal["browser", "openai", "azure"] = "browser"

class AvatarConfig(BaseModel):
    enabled: bool = False
    appearance: AvatarAppearanceConfig = AvatarAppearanceConfig()
    voice: AvatarVoiceConfig = AvatarVoiceConfig()
    expressions: AvatarExpressionsConfig = AvatarExpressionsConfig()
    input: AvatarInputConfig = AvatarInputConfig()

# Added to PersonaConfig as:
class PersonaConfig(BaseModel):
    ...
    avatar: AvatarConfig | None = None  # None = text-only agent
```

---

## New Module: persona/avatar/

```
persona/avatar/
+-- __init__.py
+-- tts.py              # TTS provider abstraction
+-- providers/
|   +-- __init__.py
|   +-- openai_tts.py   # OpenAI text-to-speech adapter
|   +-- azure_tts.py    # Azure Cognitive Services Speech adapter
|   +-- elevenlabs_tts.py  # ElevenLabs adapter
+-- visemes.py          # Viseme extraction and timing
+-- stt.py              # Speech-to-text (server-side, optional)
+-- renderer.py         # Orchestrator: text stream -> audio + visemes
+-- frontend/           # Static web frontend
    +-- index.html
    +-- app.js          # Main application logic
    +-- avatar.js       # Character renderer (Three.js / PixiJS)
    +-- lipsync.js      # Viseme -> mouth shape mapping
    +-- audio.js        # Audio playback with timing
    +-- websocket.js    # WebSocket client
    +-- style.css
```

---

## TTS Provider Abstraction

```python
# persona/avatar/tts.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class TTSChunk:
    """A chunk of synthesized audio with timing metadata."""
    audio: bytes              # Raw audio data (PCM or MP3)
    format: str               # "pcm_16000" | "mp3"
    visemes: list[Viseme]     # Lip-sync markers for this chunk
    duration_ms: int          # Duration of this audio chunk

@dataclass
class Viseme:
    """A single viseme (mouth position) with timing."""
    id: int                   # Viseme ID (0-21, standard set)
    name: str                 # Human-readable name ("AA", "OH", "EE", etc.)
    offset_ms: int            # Offset from start of chunk
    duration_ms: int          # How long to hold this viseme

class TTSProvider(ABC):
    """Abstract base for text-to-speech providers."""

    @abstractmethod
    async def synthesize(self, text: str) -> TTSChunk:
        """Convert full text to audio + visemes."""
        ...

    @abstractmethod
    async def stream(self, text_chunks: AsyncIterator[str]) -> AsyncIterator[TTSChunk]:
        """Stream text chunks -> stream audio chunks with visemes."""
        ...

class TTSProviderRegistry:
    """Registry for TTS providers (same pattern as LLM ProviderRegistry)."""
    _providers: dict[str, type[TTSProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[TTSProvider]):
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, config: dict, secrets: dict) -> TTSProvider:
        return cls._providers[name](config=config, secrets=secrets)
```

---

## Server Endpoints (Avatar-specific)

New routes are registered **only if** `config.avatar` is present and `avatar.enabled == True`.
Existing routes (`/health`, `/ready`, `/v1/chat`, `/v1/agent/info`) remain unchanged.

```python
# persona/server/avatar_endpoints.py

# GET /avatar
#   Serves the web frontend (index.html)
#   Static files served from persona/avatar/frontend/

# GET /v1/avatar/info
#   Returns avatar configuration metadata
#   Response: {
#       "enabled": true,
#       "appearance": { "type": "sprite", "asset": "..." },
#       "voice": { "provider": "openai", "voice_id": "alloy" },
#       "expressions": { ... }
#   }

# POST /v1/avatar/chat
#   Text request, returns audio + visemes + text
#   Request:  { "message": "Hello", "session_id": "..." }
#   Response: {
#       "text": "Hi there! How can I help?",
#       "audio_base64": "...",
#       "audio_format": "mp3",
#       "visemes": [
#           {"id": 0, "name": "SIL", "offset_ms": 0, "duration_ms": 100},
#           {"id": 2, "name": "AA", "offset_ms": 100, "duration_ms": 150}
#       ],
#       "expression": "speaking",
#       "session_id": "abc123"
#   }

# WebSocket /v1/avatar/stream
#   Real-time bidirectional communication
#   Client sends: { "type": "message", "text": "Hello" }
#                  { "type": "audio", "data": "<base64 PCM>" }  (voice input)
#   Server sends: { "type": "token", "content": "Hi" }
#                  { "type": "audio", "data": "<base64>", "format": "mp3" }
#                  { "type": "viseme", "id": 2, "name": "AA", "offset_ms": 100 }
#                  { "type": "expression", "name": "speaking" }
#                  { "type": "tool_call", "tool": "web_search" }
#                  { "type": "done" }

# POST /v1/avatar/stt  (optional, if stt_provider != "browser")
#   Server-side speech-to-text
#   Request:  multipart/form-data with audio file
#   Response: { "text": "transcribed text", "language": "en-US" }
```

---

## Frontend Architecture

The web frontend is a single-page application served at `/avatar`:

```
+-----------------------------------------------------------+
|                    Browser Window                          |
|                                                            |
|  +------------------------------------------------------+ |
|  |              Avatar Canvas (WebGL/Canvas2D)           | |
|  |                                                       | |
|  |         +-------------------------+                   | |
|  |         |                         |                   | |
|  |         |    Character Render     |                   | |
|  |         |    (idle/speaking/      |                   | |
|  |         |     thinking anim)      |                   | |
|  |         |                         |                   | |
|  |         +-------------------------+                   | |
|  |                                                       | |
|  +------------------------------------------------------+ |
|                                                            |
|  +------------------------------------------------------+ |
|  |  Chat transcript (scrollable)                         | |
|  |  User: Hello                                          | |
|  |  Agent: Hi there! How can I help you today?           | |
|  +------------------------------------------------------+ |
|                                                            |
|  +--------------------------------------+  +----+ +----+  |
|  |  Type a message...                    |  | Mic| | Go |  |
|  +--------------------------------------+  +----+ +----+  |
|                                                            |
+-----------------------------------------------------------+
```

### Component Responsibilities

| Component        | File                       | Role                                              |
| ---------------- | -------------------------- | ------------------------------------------------- |
| App Controller   | `app.js`                   | Manages state, coordinates components             |
| WebSocket Client | `websocket.js`             | Connects to `/v1/avatar/stream`, handles messages |
| Avatar Renderer  | `avatar.js`                | Renders 2D sprite or 3D model, plays animations   |
| Lip-sync Engine  | `lipsync.js`               | Maps viseme IDs to sprite frames / blend shapes   |
| Audio Player     | `audio.js`                 | Queues and plays audio chunks in sequence         |
| UI               | `index.html` + `style.css` | Chat transcript, input box, mic button            |

### Data Flow (streaming)

```
1. User types message (or speaks -> STT)
2. WebSocket sends: { type: "message", text: "..." }
3. Server streams back interleaved events:
   +-- { type: "expression", name: "thinking" }   -> avatar shows thinking face
   +-- { type: "token", content: "Hi" }            -> text appears in transcript
   +-- { type: "audio", data: "..." }              -> queued for playback
   +-- { type: "viseme", id: 2, offset_ms: 0 }    -> queued for lip-sync
   +-- { type: "token", content: " there!" }       -> more text
   +-- { type: "audio", data: "..." }              -> more audio
   +-- { type: "viseme", id: 5, offset_ms: 150 }   -> more visemes
   +-- { type: "done" }                             -> expression -> idle
4. Audio player plays chunks in order
5. Lip-sync engine drives mouth at audio timestamps
6. Avatar transitions back to idle when done
```

---

## CLI Extension

```bash
# Existing commands (unchanged):
persona init my-agent        # Text-only agent scaffold
persona run                  # Text REPL
persona serve                # HTTP API server
persona build                # Docker image
persona push                 # Push to registry
persona validate             # Config validation

# New commands:
persona init --avatar my-avatar-agent   # Avatar agent scaffold
persona avatar                          # Opens browser to avatar UI
persona avatar --port 9000              # Custom port
```

### persona init --avatar

Scaffolds an avatar-enabled agent:

```
my-avatar-agent/
+-- config.yaml              # Includes avatar: section
+-- requirements.txt
+-- assets/
|   +-- character.png        # Default 2D sprite sheet
|   +-- expressions.json     # Sprite frame definitions
+-- agent/
|   +-- agent.py
+-- tools/
|   +-- example_tool.py
+-- data/
```

### persona avatar

1. Loads config, checks `avatar.enabled == True`
2. Starts the FastAPI server (same as `persona serve`)
3. Opens default browser to `http://localhost:8000/avatar`

---

## Docker Changes

The Dockerfile template conditionally includes avatar assets:

```dockerfile
# In Dockerfile.jinja - avatar section
{% if avatar_enabled %}
# Copy avatar frontend
COPY persona-avatar-frontend/ /app/static/avatar/

# Copy user's avatar assets
COPY app/assets/ /app/assets/
{% endif %}
```

The build context assembles:

- Framework's avatar frontend (from `persona/avatar/frontend/`)
- User's avatar assets (from their agent's `assets/` directory)

---

## Dependencies

Avatar dependencies are optional extras in `pyproject.toml`:

```toml
[project.optional-dependencies]
# Existing:
openai = ["openai>=1.0"]
anthropic = ["anthropic>=0.20"]
docker = ["docker>=7.0"]

# New avatar extras:
avatar = ["websockets>=12.0", "aiofiles>=23.0"]
tts-openai = ["openai>=1.0"]
tts-azure = ["azure-cognitiveservices-speech>=1.30"]
tts-elevenlabs = ["elevenlabs>=1.0"]
avatar-all = [
    "websockets>=12.0",
    "aiofiles>=23.0",
    "openai>=1.0",
]
```

Install with: `pip install -e ".[avatar,tts-openai]"`

---

## Viseme Standard

We use the **Microsoft Azure viseme set** (22 visemes) as the internal standard, regardless of TTS provider:

| ID  | Name  | Mouth Shape     | Example Phonemes |
| --- | ----- | --------------- | ---------------- |
| 0   | SIL   | Closed/silent   | (silence)        |
| 1   | AE/AX | Slightly open   | "a" in "about"   |
| 2   | AA    | Wide open       | "a" in "father"  |
| 3   | AO    | Round open      | "o" in "dog"     |
| 4   | EY    | Smile stretched | "a" in "say"     |
| 5   | EH    | Half open       | "e" in "bed"     |
| 6   | IH    | Small open      | "i" in "sit"     |
| 7   | IY    | Smile narrow    | "ee" in "see"    |
| 8   | UW    | Pucker round    | "oo" in "too"    |
| 9   | OH    | Round medium    | "o" in "go"      |
| 10  | OW    | Round wide      | "ow" in "cow"    |
| 11  | AW    | Open to round   | "ou" in "out"    |
| 12  | OY    | Round to smile  | "oy" in "boy"    |
| 13  | W     | Tight round     | "w" in "we"      |
| 14  | R     | Slight pucker   | "r" in "red"     |
| 15  | L     | Tongue up       | "l" in "let"     |
| 16  | S/Z   | Teeth close     | "s" in "see"     |
| 17  | SH/CH | Pucker teeth    | "sh" in "she"    |
| 18  | TH    | Tongue out      | "th" in "the"    |
| 19  | F/V   | Bite lip        | "f" in "for"     |
| 20  | D/T/N | Tongue tap      | "d" in "dog"     |
| 21  | K/G   | Back tongue     | "k" in "key"     |

Providers that don't natively emit visemes (OpenAI, ElevenLabs) will use audio analysis or phoneme estimation to generate approximate viseme timelines.

---

## Implementation Phases

| Phase  | Scope                                                  | Depends On       |
| ------ | ------------------------------------------------------ | ---------------- |
| **2A** | Config models (`AvatarConfig`, `VoiceConfig`, etc.)    | Phase 1 complete |
| **2B** | TTS provider abstraction + OpenAI TTS adapter          | 2A               |
| **2C** | Avatar server endpoints (`/v1/avatar/*`) + WebSocket   | 2B               |
| **2D** | Web frontend with 2D sprite avatar                     | 2C               |
| **2E** | CLI `persona avatar` command + `persona init --avatar` | 2C, 2D           |
| **2F** | 3D model support (Three.js + glTF loader)              | 2D               |
| **2G** | Azure Speech TTS adapter (native visemes)              | 2B               |
| **2H** | ElevenLabs TTS adapter                                 | 2B               |
| **2I** | Speech-to-text input (microphone)                      | 2C               |
| **2J** | Docker build with avatar assets                        | 2D, 2E           |

---

## What Stays Unchanged

| Component                          | Impact                                         |
| ---------------------------------- | ---------------------------------------------- |
| `persona/core/agent.py`            | No changes                                     |
| `persona/runtime/agent_runtime.py` | No changes (avatar reads its stream output)    |
| `persona/runtime/memory.py`        | No changes                                     |
| `persona/providers/*`              | No changes                                     |
| `persona/tools/*`                  | No changes                                     |
| `persona/cli/run_cmd.py`           | No changes (text REPL stays)                   |
| `persona/cli/serve_cmd.py`         | No changes (serves text API)                   |
| `persona/cli/build_cmd.py`         | Minor: passes `avatar_enabled` flag to builder |
| `persona/server/endpoints.py`      | No changes to existing routes                  |
| `persona/server/app.py`            | Conditionally adds avatar routes               |
| Existing `config.yaml` files       | Still valid without `avatar:`                  |
| `persona init` (no flag)           | Still creates text-only agent                  |

---

## Example: Full Avatar Agent Config

```yaml
name: alex-support
version: "1.0.0"
description: "Alex - visual AI customer support agent"

agent:
  system_prompt: |
    You are Alex, a friendly and knowledgeable customer support representative
    for TechCorp. You speak in a warm, professional tone. Keep responses
    concise since they will be spoken aloud.
  model:
    provider: openai
    name: gpt-4o
    parameters:
      temperature: 0.6
      max_tokens: 300
  tools:
    - name: web_search
      type: builtin

runtime:
  streaming: true
  max_turns: 5

avatar:
  enabled: true
  appearance:
    type: 3d
    asset: "assets/alex.glb"
    background: "#0f0f1a"
    size: [800, 600]
    idle_animation: "idle_breathe"
  voice:
    provider: openai
    voice_id: "nova"
    speed: 1.0
    language: "en-US"
  expressions:
    idle: "neutral"
    thinking: "look_up"
    speaking: "talk_gesture"
    error: "apologetic"
    happy: "smile_nod"
  input:
    microphone: true
    stt_provider: browser

resources:
  cpu: "2"
  memory: "4Gi"

secrets:
  - OPENAI_API_KEY
```

---

## Implementation Phases

| Phase  | Scope                                                  | Depends On       |
| ------ | ------------------------------------------------------ | ---------------- |
| **2A** | Config models (`AvatarConfig`, `VoiceConfig`, etc.)    | Phase 1 complete |
| **2B** | TTS provider abstraction + OpenAI TTS adapter          | 2A               |
| **2C** | Avatar server endpoints (`/v1/avatar/*`) + WebSocket   | 2B               |
| **2D** | Web frontend with 2D sprite avatar                     | 2C               |
| **2E** | CLI `persona avatar` command + `persona init --avatar` | 2C, 2D           |
| **2F** | 3D model support (Three.js + glTF loader)              | 2D               |
| **2G** | Azure Speech TTS adapter (native visemes)              | 2B               |
| **2H** | ElevenLabs TTS adapter                                 | 2B               |
| **2I** | Speech-to-text input (microphone)                      | 2C               |
| **2J** | Docker build with avatar assets                        | 2D, 2E           |

---

## What Stays Unchanged

| Component                          | Impact                                         |
| ---------------------------------- | ---------------------------------------------- |
| `persona/core/agent.py`            | No changes                                     |
| `persona/runtime/agent_runtime.py` | No changes (avatar reads its stream output)    |
| `persona/runtime/memory.py`        | No changes                                     |
| `persona/providers/*`              | No changes                                     |
| `persona/tools/*`                  | No changes                                     |
| `persona/cli/run_cmd.py`           | No changes (text REPL stays)                   |
| `persona/cli/serve_cmd.py`         | No changes (serves text API)                   |
| `persona/cli/build_cmd.py`         | Minor: passes `avatar_enabled` flag to builder |
| `persona/server/endpoints.py`      | No changes to existing routes                  |
| `persona/server/app.py`            | Conditionally adds avatar routes               |
| Existing `config.yaml` files       | Still valid without `avatar:`                  |
| `persona init` (no flag)           | Still creates text-only agent                  |

---

## Example: Full Avatar Agent Config

```yaml
name: alex-support
version: "1.0.0"
description: "Alex - visual AI customer support agent"

agent:
  system_prompt: |
    You are Alex, a friendly and knowledgeable customer support representative
    for TechCorp. You speak in a warm, professional tone. Keep responses
    concise since they will be spoken aloud.
  model:
    provider: openai
    name: gpt-4o
    parameters:
      temperature: 0.6
      max_tokens: 300
  tools:
    - name: web_search
      type: builtin

runtime:
  streaming: true
  max_turns: 5

avatar:
  enabled: true
  appearance:
    type: 3d
    asset: "assets/alex.glb"
    background: "#0f0f1a"
    size: [800, 600]
    idle_animation: "idle_breathe"
  voice:
    provider: openai
    voice_id: "nova"
    speed: 1.0
    language: "en-US"
  expressions:
    idle: "neutral"
    thinking: "look_up"
    speaking: "talk_gesture"
    error: "apologetic"
    happy: "smile_nod"
  input:
    microphone: true
    stt_provider: browser

resources:
  cpu: "2"
  memory: "4Gi"

secrets:
  - OPENAI_API_KEY
```
