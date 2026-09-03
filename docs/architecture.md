# NAV v0 Architecture — Design Spec

## What is NAV?

NAV (Navigate · Augment · Venture) is a personal AI system designed to evolve across multiple capabilities and interfaces. For v0, NAV establishes three core capabilities:

1. **Cognition** — Understand requests, reason, and produce responses.
2. **Memory** — Retain and retrieve useful user context.
3. **Research** — Discover, retrieve, and synthesize external information.

The primary interface is voice-first, with text as a fallback. The AI layer uses a hybrid approach: local models, free/low-cost APIs, and paid frontier APIs.

---

## Architectural Principle

> **Stable contracts over stable implementations.**

NAV depends on abstract capability interfaces and contracts rather than specific vendors, models, databases, or frameworks. The implementation can change without requiring NAV Core to change.

```text
                     NAV v0
                       │
                  ┌────▼────┐
                  │ NAV Core │
                  └────┬────┘
                       │
             ┌─────────┼─────────┐
             │         │         │
         Cognition   Memory   Research
             │         │         │
             └─────────┼─────────┘
                       │
                supporting layers
                       │
         ┌─────────────┼─────────────┐
         │             │             │
      AI Gateway      Data        Security
         │
    Model Router (future)
         │
   ┌─────┼─────┐
   │     │     │
 Local  Free  Paid
   AI   APIs   APIs
Interfaces:

Voice (Primary — future)
Text (Fallback — future)
1. Core Boundary (core/)
The nucleus of NAV. Intentionally kept small and isolated from vendor logic, databases, scrapers, and UI code.

core/contracts/: Defines typed interfaces (Capability, Request, Response, NavContext, AIGateway, MemoryCapabilityInterface, ResearchCapabilityInterface).
core/context/: Light context models (UserContext, SessionContext, ConversationContext, NavContext).
core/capabilities/: Capability registry for dynamic discovery and registration without tight coupling.
core/orchestration/: Lightweight routing mechanism delegating requests to registered capabilities.
core/log.py: Standard-library logging foundation.
Key rule: core/ must never import specific vendor packages (e.g., openai, anthropic, httpx, psycopg2).

2. Capability Boundaries (capabilities/)
Replaceable functional modules:

capabilities/cognition/: Understanding, reasoning, and response generation. (S3: Real AI-powered via AIGateway)
capabilities/memory/: Retention, retrieval, and lifecycle of user context. (Stub — S6)
capabilities/research/: Information discovery, extraction, and synthesis. (Stub — S7)
3. AI Layer (ai/) — Implemented in S3
The AI layer sits between capabilities and external model providers. It is the only part of NAV that knows about specific AI vendors.

text

ai/
├── errors.py              # NAV-level AI error hierarchy
├── gateway/
│   └── default_gateway.py # AIGateway implementation (provider selection)
└── providers/
    ├── ollama_provider.py  # Local Ollama adapter (default)
    └── openai_provider.py  # OpenAI API adapter (alternative)
Provider Abstraction
text

AIGateway (core contract)
    │
    ├── OllamaProvider   (local, free, no key)
    ├── OpenAIProvider   (paid API, requires key)
    └── FutureProvider   (any future backend)
Provider Selection
Controlled by the NAV_AI_PROVIDER environment variable:

ollama (default) — Local model via Ollama HTTP API
openai — OpenAI Chat Completions API
Error Translation
Provider-specific errors are translated into NAV-level types before reaching Core:

text

Provider Error (e.g., HTTP 401, timeout)
      ↓
Provider Adapter
      ↓
NAV AI Error (ConfigurationError / ProviderError)
      ↓
Cognition
      ↓
Structured Response
4. Interface Boundaries (interfaces/) — Future
interfaces/voice/: Audio capture, STT, and TTS output pipelines. (S4)
interfaces/text/: Terminal, CLI, and standard text fallbacks.
5. Security Boundary (security/) — Future
First-class enforcement plane for authentication, authorization, secret storage, sandboxed tool execution, privacy controls, and audit trails.

6. Data Boundary (data/) — Future
Workspace for local persistent databases, embeddings, and vector stores (all excluded from Git via .gitignore).

7. Status & Decisions
Implemented
Sprint    Deliverable
S1    Physical directory structure, stable vendor-agnostic contracts, CapabilityRegistry, Orchestrator, Cognition stub, test suite
S2    pyproject.toml, Ruff, Mypy, logging foundation, .env.example, .gitignore
S3    Real AI Cognition via AIGateway, Ollama provider (default), OpenAI provider (alternative), error hierarchy, 30 tests
Intentionally Not Locked Yet
Database or vector store technology (S6)
Speech-to-text / Text-to-speech tools (S4)
Web scraping and research search providers (S7)
UI frameworks or transport protocols
Model routing policy engine (S5)
8. S3 Architecture Validation
Did the S1/S2 Core abstraction survive contact with real AI providers?

Yes. Zero changes were made to any file under core/. The existing AIGateway.generate(AIRequest) -> AIResponse contract mapped cleanly to both Ollama and OpenAI APIs. The AIMessage role/content structure is identical to both providers' message formats.

The Replacement Test (§27)
"We're dropping the current provider and using a different one."

What changes: One file in ai/providers/ + environment variables.
What does NOT change: Core, Orchestrator, Cognition, Context, Registry, contracts, tests.
