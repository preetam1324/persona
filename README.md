# Persona

**The framework for embodied, voiced AI personas.**

Persona is a free, open-source Python framework for building AI agents that don't just chat — they have a **face, a voice, and a presence**. Define a persona in YAML, give it a visual avatar with real-time lip-sync and expressions, wire in tools, and deploy anywhere as a Docker container.

Most agent frameworks stop at text. Persona owns the **last mile of human-agent interaction**: embodiment, voice, and personality.

---

## Why Persona?

Agent orchestration is a crowded space. Persona is different — it's the framework that treats **embodiment as a first-class citizen**:

- 🎭 **Visual avatars** — 2D sprites or 3D (glTF/GLB) characters that render in the browser
- 🗣️ **Real-time voice** — pluggable TTS (OpenAI, Azure Speech, ElevenLabs) with streaming audio
- 👄 **Lip-sync & expressions** — viseme-driven mouth movement and emotion-aware facial expressions (idle, thinking, speaking, happy, concerned)
- 🎙️ **Voice input** — speech-to-text so users can _talk_ to your persona
- 🧩 **Tools & reasoning** — the full agentic loop (reason → use tools → respond) underneath the face
- 📦 **Ship as a container** — avatar frontend, TTS pipeline, and assets all package into one Docker image

Your persona can be a branded receptionist, a tutor, a support rep, or a virtual influencer — a real character, not a chat box.

---

## Quickstart

```bash
pip install persona

# Create a persona with an avatar
persona init my-persona --avatar
cd my-persona

# Edit config.yaml — set the personality, voice, and appearance
persona avatar       # Launch the avatar in your browser (voice + face)
persona run          # Text-only interactive chat
persona serve        # HTTP + WebSocket server
persona build        # Package into a Docker image
```

---

## Define a persona in YAML

A complete embodied persona — personality, brain, voice, and face — in one config file, no code required:

```yaml
name: alex
description: "A friendly customer support persona"

agent:
  system_prompt: |
    You are Alex, a warm and helpful customer support representative.
  model:
    provider: openai
    name: gpt-4o
  tools:
    - name: web_search
      type: builtin

avatar:
  enabled: true
  appearance:
    type: sprite # "sprite" (2D) or "3d" (glTF/GLB)
    asset: assets/alex.png
    idle_animation: breathing
  voice:
    provider: openai # openai | azure | elevenlabs
    voice_id: alloy
    language: en-US
  expressions:
    idle: neutral
    thinking: eyebrows_raised
    speaking: talking
    happy: smile
  input:
    microphone: true # let users speak to Alex
    stt_provider: browser
```

That's it — `persona avatar` gives Alex a face, a voice, and the ability to hold a spoken conversation.

---

## How it works

Persona layers embodiment on top of a standard agentic runtime:

```
config.yaml → AgentRuntime → LLM + Tools → streaming text
                                              │
                                              ▼
                         TTS Provider → audio + viseme timeline
                                              │
                                              ▼
                    WebSocket → Browser (character renderer,
                                lip-sync, expressions, audio)
```

The reasoning core (LLM, tools, memory) is fully functional on its own — the avatar layer is **additive and opt-in**. Text-only agents work unchanged; add an `avatar:` block to give them a body.

---

## Features

|                     |                                                                                |
| ------------------- | ------------------------------------------------------------------------------ |
| **Embodiment**      | 2D sprite & 3D (glTF/GLB) avatars, idle animations, expression system          |
| **Voice out**       | Streaming TTS via OpenAI, Azure Speech, ElevenLabs                             |
| **Voice in**        | Speech-to-text (browser Web Speech API, OpenAI, Azure)                         |
| **Lip-sync**        | Viseme-timeline-driven mouth movement synced to audio                          |
| **Reasoning**       | Tool-using agent loop with pluggable LLM providers (OpenAI, Anthropic, Ollama) |
| **Hot-swap models** | Change the underlying model at runtime via API — no restart                    |
| **Tools**           | Built-in (web search, code exec, file read) + custom Python tools              |
| **Deploy**          | One-command Docker packaging; runs anywhere                                    |

---

## CLI

| Command                        | Purpose                                         |
| ------------------------------ | ----------------------------------------------- |
| `persona init [name] --avatar` | Scaffold a new embodied persona                 |
| `persona avatar`               | Launch the avatar (face + voice) in the browser |
| `persona run`                  | Text-only interactive chat                      |
| `persona serve`                | Start HTTP + WebSocket server                   |
| `persona validate`             | Validate config, tools, and providers           |
| `persona build`                | Build a Docker image                            |
| `persona push`                 | Push the image to a registry                    |

---

## Documentation

- [Architecture](docs/architecture.md) — the agentic core
- [Avatar Architecture](docs/avatar-architecture.md) — the embodiment layer
- [Contributing](CONTRIBUTING.md)

## License

Apache-2.0
