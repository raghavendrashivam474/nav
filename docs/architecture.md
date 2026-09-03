# NAV v0 Architecture — Sprint 1 Design Spec

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
text

                     NAV v0
                       │
                  ┌────▼────┐
                  │ NAV Core│
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
    Model Router
         │
   ┌─────┼─────┐
   │     │     │
 Local Free   Paid
   AI   APIs   APIs
Interfaces:
Voice (Primary)
Text (Fallback)

text


---

## 1. Core Boundary (core/)
The nucleus of NAV. Intentionally kept small and isolated from vendor logic, databases, scrapers, and UI code.
- **core/contracts/**: Defines typed interfaces (Capability, Request, Response, NavContext, AIGateway, MemoryCapabilityInterface, ResearchCapabilityInterface).
- **core/context/**: Light context models (UserContext, SessionContext, ConversationContext, NavContext).
- **core/capabilities/**: Capability registry for dynamic discovery and registration without tight coupling.
- **core/orchestration/**: Lightweight routing mechanism delegating requests to registered capabilities.

## 2. Capability Boundaries (capabilities/)
Replaceable functional modules:
- **capabilities/cognition/**: Understanding, reasoning, and response generation.
- **capabilities/memory/**: Retention, retrieval, and lifecycle of user context.
- **capabilities/research/**: Information discovery, extraction, and synthesis.

## 3. Hybrid AI Layer (i/)
- **i/gateway/**: Uniform invocation gateway.
- **i/router/**: Model routing policy engine based on complexity, privacy, cost, latency, and context size.
- **i/providers/**: Separated into local/ (Ollama/Llama), ree/ (open/low-cost APIs), and paid/ (frontier model APIs).
- **i/policies/**: Routing constraints, cost caps, and fallback policies.

## 4. Interface Boundaries (interfaces/)
- **interfaces/voice/**: Audio capture, STT, and TTS output pipelines.
- **interfaces/text/**: Terminal, CLI, and standard text fallbacks.

## 5. Security Boundary (security/)
First-class enforcement plane for authentication, authorization, secret storage, sandboxed tool execution, privacy controls, and audit trails.

## 6. Data Boundary (data/)
Workspace for local persistent databases, embeddings, and vector stores (all excluded from Git via .gitignore).

---

## 7. Status & Non-Locked Decisions

### Implemented in S1
- Physical directory structure and architectural skeleton.
- Stable, vendor-agnostic Python contracts.
- Central CapabilityRegistry and Orchestrator.
- Cognition capability stub and full verification unit test suite.
- Architectural and development documentation.

### Intentionally Not Locked Yet
- Specific AI models / vendors (e.g., OpenAI, Anthropic, Ollama).
- Database or vector store technology (e.g., SQLite, PostgreSQL, Chroma).
- Speech-to-text / Text-to-speech tools.
- Web scraping and research search providers.
- UI frameworks or transport protocols.
