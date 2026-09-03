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
    Model Router (S5)
         │
   ┌─────┼─────┐
   │     │     │
 Local  Free  Paid
   AI   APIs   APIs
Interfaces:
Voice (Primary — S4)
Text (Fallback)
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
3. AI Layer (ai/) — Upgraded in S5
The AI layer sits between capabilities and external model providers. It isolates the rest of the application from specific vendors and chooses the appropriate backend dynamically.

text

ai/
├── errors.py              # NAV-level AI error hierarchy with routing errors
├── gateway/
│   └── default_gateway.py # AIGateway implementation with router integration
├── providers/
│   ├── base.py            # AIProvider structural protocol
│   ├── ollama_provider.py # Local Ollama adapter (free, local)
│   └── openai_provider.py # OpenAI API adapter (paid, remote)
└── routing/
    ├── __init__.py        # Public routing API exports
    ├── router.py          # Policy-driven ModelRouter implementation
    └── types.py           # Structured RoutingContext, ProviderMetadata, and Decisions
Provider Abstraction
text

AIGateway (core contract)
    │
    ▼
ModelRouter (routing policy engine)
    │
    ├── OllamaProvider   (local, free, standard-quality)
    ├── OpenAIProvider   (remote, paid, high-quality)
    └── FutureProvider   (any future backend satisfying AIProvider Protocol)
Model Router Design (S5)
NAV selects an AI provider dynamically based on policy, constraints, and soft preferences:

Constraints (Hard Rules): Things NAV must not violate.

local_only: Removes remote providers to protect privacy.
no_paid: Removes paid providers to respect cost constraints.
If no provider satisfies all hard constraints, a structured RoutingError is raised immediately.
Preferences (Soft Rules): Things NAV optimizes when possible.

quality_requirement == "high": Favors high-quality providers (e.g., OpenAI).
cost_preference == "low": Favors free/local models (e.g., Ollama).
complexity == "simple": Favors lightweight, low-latency local models.
privacy == "local_only": Guarantees that only local models are matched.
Fallback Strategy:

The router ranks remaining eligible providers and returns a primary selection plus a fallback chain.
If the primary provider fails, the gateway automatically executes the request on the fallback provider.
Crucially, fallback operations must re-enforce hard constraints. A private request that fails locally will never fall back to a cloud model, preventing data leaks.
Error Translation
Provider-specific errors are translated into NAV-level types before reaching Core:

text

Provider Error (e.g., HTTP 401, timeout)
      ↓
Provider Adapter
      ↓
NAV AI Error (ConfigurationError / ProviderError / RoutingError)
      ↓
Cognition
      ↓
Structured Response
4. Interface Boundaries (interfaces/) — Implemented in S4
interfaces/voice/: Audio capture, STT, and TTS output pipelines.
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
S4    Voice Interface supporting offline OS-based TTS (pyttsx3) and high-accuracy STT (faster-whisper), 29 tests
S5    Policy-driven Model Router, structured routing requests/context, robust fallback systems protecting privacy, 20 new tests
Intentionally Not Locked Yet
Database or vector store technology (S6)
Web scraping and research search providers (S7)
UI frameworks or transport protocols
8. S5 Architecture Validation
Did the AI Gateway abstraction remain stable while implementing dynamic routing?

Yes. The AIGateway protocol was not changed, and the calling capability (CognitionCapability) remains entirely unaware of which provider is executing its requests. The routing parameters are optionally passed inside AIRequest.options["routing"], preserving full backward compatibility.
