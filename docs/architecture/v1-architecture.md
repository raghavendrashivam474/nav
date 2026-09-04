# NAV v1 Architecture Specification

**Sprint Baseline:** S11 (evolving from v0.10 `2e0e706`)  
**Status:** Approved Architectural Baseline  
**North Star:**  
> *"Can NAV become a persistent, personal, human-in-the-loop intelligence system that understands context, helps investigate and build things, remembers what matters, and remains useful across time?"*

---

## 1. Architectural Principles

1. **North Star Alignment**: Architecture exists solely to carry long-term personal intelligence without collapse. Avoid premature distributed systems and unnecessary abstractions.
2. **Contracts over Concrete Implementations**: Subsystems communicate strictly through typed, abstract contracts and protocols.
3. **Strict Dependency Hierarchy**:  
   `Core Contracts` $\leftarrow$ `Capabilities` $\leftarrow$ `Providers / Repositories / Adapters` $\leftarrow$ `External Systems / I/O`  
   Core never imports concrete implementations or external vendors.
4. **State Isolation**: Separate ephemeral execution state, session-scoped context, and long-term durable memory. No component mutates state outside its declared boundary.
5. **Independent Enforcement Planes**: Security and policy are non-bypassable boundaries across all capability flows.
6. **External Systems Remain External**: External projects (e.g., Avni) are integrated strictly via adapter boundaries. NAV never absorbs external system internals.

---

## 2. High-Level System Architecture

```text
                               ┌────────────────────────────────┐
                               │       User / Interfaces        │
                               │  (Voice, CLI, Future Clients)  │
                               └───────────────┬────────────────┘
                                               │
                                               ▼
                               ┌────────────────────────────────┐
                               │           NAV Core             │
                               │  - Contracts & Dataclasses     │
                               │  - Capability Registry         │
                               │  - Request Orchestrator        │
                               │  - Context Coordination        │
                               └───────┬───────────────┬────────┘
                                       │               │
                     ┌─────────────────┴────┐     ┌────┴─────────────────┐
                     ▼                      ▼     ▼                      ▼
          ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
          │Cognition Capability│ │ Memory Capability  │ │Research Capability │
          └─────────┬──────────┘ └─────────┬──────────┘ └─────────┬──────────┘
                    │                      │                      │
                    ▼                      ▼                      ▼
          ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
          │     AI Gateway     │ │ Memory Repository  │ │ Providers / Cache  │
          │ (Model Router &    │ │ (SQLite Engine /   │ │ (SearchRouter, DDG,│
          │  Fallback Chain)   │ │  Future Backends)  │ │  Brave, Extractor) │
          └─────────┬──────────┘ └────────────────────┘ └────────────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌──────────────────┐ ┌──────────────────┐
│  Ollama (Local)  │ │   OpenAI (API)   │
└──────────────────┘ └──────────────────┘
```

---

## 3. Boundary Definitions

### 3.1 NAV Core
- **Location:** `core/`
- **Role:** Pure definitions, coordination, and invariants.
- **Owns:**
  - `Capability`, `Context`, `Memory`, `Research`, `AI`, and `Security` abstract contracts.
  - `CapabilityRegistry`: Registration and lookup of capability instances.
  - `Orchestrator`: Stateless request routing between callers and capabilities.
  - `ContextManager` Contract: Coordination interface for session, user, and conversation state.
  - Central logging facility (`core.log`).
- **Must NEVER contain:** Concrete providers, HTTP clients, vendor SDKs, raw SQL/database connections, UI rendering logic, or capability-specific heuristics.

### 3.2 NAV Runtime
- **Role:** How NAV boots, wires, and runs in a concrete environment.
- **Responsibilities:**
  - Instantiates providers based on environment/config (`NAV_AI_PROVIDER`, `NAV_SEARCH_PROVIDER`, etc.).
  - Binds repositories to storage paths.
  - Registers instantiated capabilities into `CapabilityRegistry`.
  - Configures `Orchestrator` and launches interface boundaries (CLI, Voice).

### 3.3 Capabilities
- **Location:** `capabilities/<name>/`
- **Role:** Discrete functional intelligence domains implementing `core.contracts.Capability`.
- **Pattern:** Dual inheritance of `Capability` (for generic Orchestrator invocation) and `<Name>CapabilityInterface` (for direct in-process typed invocation).
- **Standard Capabilities:**
  - **Cognition:** Intent resolution, prompt synthesis, reasoning via `AIGateway`, and memory-informed generation.
  - **Memory:** Explicit long-term knowledge retention and retrieval backed by `MemoryRepository`.
  - **Research:** Deep multi-turn investigation, discovery, concurrent retrieval, evidence extraction, and synthesis.

### 3.4 Shared Infrastructure (AI Layer)
- **Location:** `ai/`
- **Role:** Shared intelligent routing infrastructure used across multiple capabilities (Cognition, Research Synthesis, Future Agents).
- **Components:**
  - `AIGateway`: Gateway interface with fallback chain execution.
  - `ModelRouter`: Policy-based routing applying hard constraints (privacy, cost) and soft preferences (quality, latency).
  - **Concrete Providers:** `OllamaProvider` (local), `OpenAIProvider` (remote).

### 3.5 Interfaces & Frontends
- **Location:** `interfaces/<type>/`
- **Role:** Human-facing interaction channels (e.g., `interfaces/voice/`).
- **Boundary Rule:** Frontends consume Core contracts or route requests through Orchestrator. A request originated via Voice produces a standard `core.contracts.Request` indistinguishable from any programmatic caller.

---

## 4. State & Context Architecture

NAV explicitly differentiates state lifecycles to prevent memory pollution and state confusion:

| Category | Lifetime | Examples / Ownership |
|---|---|---|
| **Ephemeral** | Single Request Cycle | Request ID, raw audio, temp tokens |
| **Session Context** | Active Interaction Thread | `ResearchSessionContext`, Voice turns |
| **Long-Term State** | Durable / Persistent | `MemoryRecord` (SQLite), User Profile |

### Context Separation Principles
- **Memory $\neq$ Session Context:** Research sessions and conversation scratchpads are volatile and evicted on TTL/termination. Only explicitly committed findings or user "remember" directives persist to durable Memory.
- **Context Ownership:**
  - `core.contracts.NavContext`: The top-level composition of User, Session, Conversation, and Capability context.
  - Per-capability session stores (e.g., `ResearchContextStore`) manage specialized multi-turn thread state.

---

## 5. Identity Boundaries

To support personal multi-agent and multi-device intelligence, identities are strictly partitioned:

- **User Identity (`UserContext.user_id`):** The human user interacting with NAV. Owns preferences and private long-term memory.
- **NAV Identity:** The persistent assistant persona and intelligence orchestrator.
- **Voice / Persona Identity:** The audio manifestation and rendering style (e.g., provided by Avni or local TTS). Changing the voice persona does not alter NAV identity or user memory.

---

## 6. Security & Policy Plane

- **Invariant:** External, retrieved, or untrusted content is never treated as instruction or authority.
- **Enforcement:**
  - Input boundaries validate and wrap untrusted external data (e.g., `<untrusted_source_data>` delimiters in Research).
  - `ModelRouter` enforces strict privacy constraints (`local_only` routing prevents data egress).
  - Full authorization, audit logging, and tool sandbox enforcement will integrate via the unified Security Plane (S20).

---

## 7. External Systems & Provider Model

External systems (such as Avni) integrate cleanly through the Adapter/Provider pattern:

1. NAV defines abstract protocols (`SpeechToText`, `TextToSpeech`, `SearchProvider`, `AIGateway`).
2. Concrete Adapters translate NAV protocols into external API / IPC / RPC calls.
3. NAV never references or imports external project internals.

---

*Verified against baseline v0.10. Foundation for S12+.*
