# NAV v0 Architecture — Design Spec

## What is NAV?

NAV (Navigate · Augment · Venture) is a personal AI system designed to evolve across multiple capabilities and interfaces. For v0, NAV establishes three core capabilities:

1. **Cognition** — Understand requests, reason, and produce responses.
2. **Memory** — Retain and retrieve useful user context across sessions (S6).
3. **Research** — Discover, retrieve, and synthesize external information.

The primary interface is voice-first, with text as a fallback. The AI layer uses a hybrid approach: local models, free/low-cost APIs, and paid frontier APIs.

---

## Architectural Principle

> **Stable contracts over stable implementations.**

NAV depends on abstract capability interfaces and contracts rather than specific vendors, models, databases, or frameworks. The implementation can change without requiring NAV Core to change.

`	ext
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
         │             │
    Model Router    SQLite
         │          Storage
   ┌─────┼─────┐
   │     │     │
 Local  Free  Paid
   AI   APIs   APIs

Interfaces:
Voice (Primary — S4)
Text (Fallback)
1. Core Boundary (core/)
The nucleus of NAV. Intentionally kept small and isolated from vendor logic, databases, scrapers, and UI code.

core/contracts/: Typed interfaces (Capability, Request, Response, NavContext, AIGateway, MemoryCapabilityInterface, ResearchCapabilityInterface).
core/context/: Light context models (UserContext, SessionContext, ConversationContext, NavContext).
core/capabilities/: Capability registry for dynamic discovery and registration without tight coupling.
core/orchestration/: Lightweight routing mechanism delegating requests to registered capabilities.
core/log.py: Standard-library logging foundation.
Key invariant: core/ must never import specific vendor packages (e.g. openai, httpx) or storage technologies (e.g. sqlite3).

2. Capability Boundaries (capabilities/)
Replaceable functional modules:

capabilities/cognition/: Understanding, reasoning, and response generation (S3 AI Gateway + S6 Memory context injection).
capabilities/memory/: Retention, retrieval, and lifecycle of user context (S6 SQLite-backed, fully replaceable).
capabilities/research/: Information discovery, extraction, and synthesis (Stub — S7).
3. Memory Layer (capabilities/memory/) — Implemented in S6
text

Cognition / Core
       │
       ▼ (MemoryCapabilityInterface)
MemoryCapability
       │
       ▼
MemoryService (persistence decisions, intent detection)
       │
       ▼
MemoryRepository ABC
       │
       ▼
SQLiteMemoryRepository (sqlite3 stdlib, data/nav_memory.db)
Invariants:
Core does not import sqlite3.
Cognition does not execute SQL.
Storage backend is swappable behind MemoryRepository.
Deterministic retrieval without heavy vector database dependencies.
All local state is isolated in data/nav_memory.db and gitignored.
4. AI Layer (ai/) — Upgraded in S5
Policy-driven Model Router dynamically selecting between local Ollama and remote OpenAI providers while enforcing hard privacy constraints.

5. Interface Boundaries (interfaces/) — Implemented in S4
Voice capture, Whisper STT, pyttsx3 TTS, and CLI fallback.

6. Status & Decisions
Implemented
Sprint    Deliverable
S1    Architecture skeleton, contracts, CapabilityRegistry, Orchestrator, Cognition stub
S2    pyproject.toml, Ruff, Mypy, logging, .gitignore
S3    Real AI Cognition via AIGateway, Ollama & OpenAI providers
S4    Voice Interface (pyttsx3 TTS + Whisper STT)
S5    Policy-driven Model Router with privacy-preserving fallbacks
S6    Persistent Memory (SQLite backend, MemoryRepository abstraction, Cognition integration)
Future / Not Locked Yet
Web scraping and research search providers (S7)
Vector database / semantic embeddings (Post-v0)
Security & authorization plane
