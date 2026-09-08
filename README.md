# NAV — Navigate · Augment · Venture

**Persistent personal intelligence that understands context, investigates and builds, remembers what matters, and remains useful across time.**

---

## What is NAV?

NAV is a modular personal intelligence system. It is not a single-purpose chatbot or a voice-wrapper around an LLM. It is an evolving architecture of explicit, composable cognitive capabilities designed to acquire information, reason over it, act on conclusions, and observe the results — persistently, across sessions and contexts.

NAV's capabilities are defined by **stable contracts** and **replaceable implementations**, meaning the system can evolve its internals — including AI providers, models, and infrastructure — without breaking the boundaries that other components depend on.

---

## North Star

> Persistent personal intelligence that understands context, investigates/builds, remembers what matters, and remains useful across time.

NAV is moving toward a future where it maintains continuity across:

```
Context → Memory → Identity → Environment → Device → Runtime → Continuity
```

Some of these layers are implemented today. Others represent the architectural direction of the project. The current implementation status of each layer is documented in the sprint completion reports under [`docs/`](docs/).

---

## Current State

| Field | Value |
|---|---|
| **Version** | v2.7 |
| **Latest Sprint** | S30 — Observation |
| **Commit** | `0a642ca` |
| **Status** | **COMPLETE · SHIPPED · FROZEN** |

---

## Cognitive Architecture

NAV's cognitive capabilities follow an explicit eight-stage trajectory, each delivered as a discrete sprint with its own contract, implementation, and test suite:

```
  Acquire  (S23)
     ↓
  Represent (S24)
     ↓
  Synthesize (S25)
     ↓
  Compare   (S26)
     ↓
  Reason    (S27)
     ↓
  Decide    (S28)
     ↓
  Act       (S29)
     ↓
  Observe   (S30)
```

Each capability is a self-contained module with a defined interface. Capabilities compose into higher-order cognitive flows but are not tightly coupled to one another's internals.

### Conceptual System Overview

```
                          NAV
                           │
                    NAV Core / Runtime
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    Capabilities      AI Gateway        Security
    (S23 – S30)      (model-agnostic)   (Sx1)
         │                 │                 │
         │          Provider / Model         │
         │            Abstraction            │
         │                                   │
         └───────────────┬───────────────────┘
                         │
                   Cognitive Flow

   Acquire → Represent → Synthesize → Compare
           → Reason → Decide → Act → Observe
```

> **Note:** This diagram represents real architectural boundaries present in the repository. It is not aspirational — the components shown exist as implemented modules. See [`docs/architecture/`](docs/architecture/) for detailed design decisions.

---

## Architecture Principles

NAV is built on a small set of non-negotiable design principles:

- **Stable contracts over stable implementations.** Interfaces between capabilities are versioned and frozen upon sprint completion. The code behind them may change freely.
- **Modular capabilities.** Each cognitive capability is an independent module. No capability should require intimate knowledge of another's internals.
- **Replaceable AI layer.** NAV is model-agnostic. AI providers and models are routed through the AI Gateway and can be swapped without modifying capability logic.
- **Explicit security boundaries.** Authority, trust, and data access are governed by the security architecture (see below), not by convention.
- **Hybrid and evolvable technology.** NAV does not commit permanently to a single framework, runtime, or infrastructure choice. Technology decisions are revisited as the system grows.

---

## Security

NAV includes an explicit security and authority architecture, delivered through the **Sx1 Blackbox** security sequence.

Key properties:

- Security boundaries are defined as first-class architectural elements, not afterthoughts.
- Authority and trust models are documented and enforced at the contract level.
- The Sx1 implementation is **complete and frozen**.

For detailed security architecture, threat models, and authority specifications, see:

- [`docs/sx1/`](docs/sx1/) <!-- VERIFY: confirm exact path -->
- [`docs/architecture/decisions/`](docs/architecture/decisions/)

> **Note:** Future security work (Sx2 and beyond) is part of the project backlog but is **not yet implemented**. Do not assume capabilities beyond Sx1 are currently enforced.

---

## AI Architecture

NAV's AI integration is handled through an **AI Gateway** that abstracts provider and model selection away from capability logic.

### Key properties

- **Model-agnostic.** Capabilities do not call a specific model directly. They request cognitive operations through the gateway.
- **Provider-replaceable.** Switching between local and hosted providers is a configuration change, not a code change.
- **Credential-isolated.** API keys and provider credentials are managed through environment configuration and are never embedded in capability code.

### Configuration

<!-- VERIFY: Replace the block below with the actual env vars and config file paths from your repo. Do not guess. -->

```bash
# Example — verify against your actual .env / config
NAV_AI_PROVIDER=         # e.g., "openai", "ollama", etc.
NAV_AI_MODEL=            # e.g., model identifier
NAV_AI_API_KEY=          # required for hosted providers
NAV_AI_BASE_URL=         # required for local/self-hosted providers
```

For the authoritative list of supported providers, configuration variables, and integration details, see:

- [`core/ai/`](core/ai/) <!-- VERIFY: confirm path -->
- [`docs/architecture/`](docs/architecture/)

---

## Development

### Prerequisites

- Python <!-- VERIFY: e.g., 3.11+ — check pyproject.toml -->
- <!-- VERIFY: any other system deps, e.g., uv, pip, poetry -->

### Setup

```bash
git clone <repository-url>
cd nav

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Install development dependencies
pip install -e ".[dev]"          # VERIFY: check pyproject.toml for exact target
```

### Tests

```bash
pytest                           # VERIFY: confirm test runner and any flags
```

The full test suite validates all frozen sprint contracts (S23–S30, Sx1). All tests should pass on the `main` branch at the v2.7 tag.

### Linting and Formatting

```bash
ruff check .                     # VERIFY: confirm linter
ruff format .                    # VERIFY: confirm formatter
```

### Type Checking

```bash
mypy .                           # VERIFY: confirm mypy config / flags
```

---

## Running NAV

<!-- VERIFY: Replace with the actual entry point, CLI command, or run instructions from your repo. -->

```bash
# Example — verify against actual entry point
python -m nav                    # or: nav run, etc.
```

For AI integration, ensure the required environment variables are set (see [AI Architecture](#ai-architecture) above). Tests that require live AI credentials are skipped automatically when credentials are absent.

---

## Project Evolution

NAV has evolved through several major phases:

| Phase | Focus | Status |
|---|---|---|
| **NAV v0** | Initial concept — Cognition, Memory, Research | Historical |
| **NAV v2 (S23–S30)** | Explicit modular cognitive capabilities | **Complete** |
| **Sx1 Blackbox** | Security and authority architecture | **Complete** |
| **Continuity layers** | Context, Memory, Identity, Environment, Device, Runtime | In progress / Future |

### v0 → v2 Transition

NAV v0 explored the concept of a personal AI assistant organized around three broad capabilities (Cognition, Memory, Research) with a voice-first interface direction. That framing has been superseded.

NAV v2 restructured the project around an explicit cognitive capability sequence (Acquire through Observe), a formal AI Gateway, and a first-class security architecture. The v0 concepts informed the v2 direction but do not describe the current system.

---

## Sprint Status

| Sprint | Capability | Status |
|---|---|---|
| S23 | Acquire | ✅ Complete / Frozen |
| S24 | Represent | ✅ Complete / Frozen |
| S25 | Synthesize | ✅ Complete / Frozen |
| S26 | Compare | ✅ Complete / Frozen |
| S27 | Reason | ✅ Complete / Frozen |
| S28 | Decide | ✅ Complete / Frozen |
| S29 | Act | ✅ Complete / Frozen |
| S30 | Observe | ✅ Complete / Frozen |
| Sx1 | Security (Blackbox) | ✅ Complete / Frozen |

> Sprints beyond S30 are part of NAV's long-term direction but are **not yet started**. No S31+ implementation exists in the repository.

---

## Documentation

| Resource | Location |
|---|---|
| Sprint completion reports | [`docs/s23/`](docs/s23/) – [`docs/s30/`](docs/s30/) |
| Security documentation | [`docs/sx1/`](docs/sx1/) <!-- VERIFY --> |
| Architecture decisions | [`docs/architecture/decisions/`](docs/architecture/decisions/) |
| AI Gateway details | [`core/ai/`](core/ai/) <!-- VERIFY --> |

---

## Contributing

NAV's architecture depends on contract stability. If you are contributing:

1. **Do not modify frozen sprint contracts** (S23–S30, Sx1) without explicit justification.
2. **Do not couple capabilities** that are currently independent.
3. **Do not hard-code AI providers or models** into capability logic — use the AI Gateway.
4. **Run the full test suite** before submitting changes.

---

## License

Aryntra NAV is licensed under the Apache License 2.0.

See [LICENSE](LICENSE) for the license notice and terms.
