# NAV v0 — Roadmap

This document outlines the planned sprint progression for NAV v0. Sprint scopes may evolve based on review feedback and technical discoveries.

---

## Completed Sprints

### ✅ S1 — Project Structure & Architectural Skeleton
**Goal:** Establish boundaries, contracts, and the architectural skeleton.
**Outcome:** Full directory structure, typed contracts, registry, orchestrator, cognition stub, 4 passing tests.
**Status:** Complete. See [S1 Completion Report](s1/completion-report.md).

### ✅ S2 — Prerequisites & Environment Verification
**Goal:** Make the development environment reproducible and professionally verifiable.
**Outcome:** `pyproject.toml`, virtual environment, Ruff, Mypy, logging foundation, 8 passing tests, full documentation.
**Status:** Complete. See [S2 Completion Report](s2/completion-report.md).

---

## Planned Sprints

### ⬜ S3 — First Real Capability (Cognition + AI Provider)
**Goal:** Wire the first real AI provider into the Cognition capability and prove the Core abstraction works end-to-end.
**Scope:**
- Integrate one AI provider (e.g., OpenAI, Ollama, or a free-tier API)
- Implement real `CognitionCapability.invoke()` replacing the S1 stub
- Implement `AIGateway` for uniform provider invocation
- Basic model routing (single provider, no fallback yet)
- Environment variable loading for API keys
- Integration tests for live AI calls (skippable in CI)
**Key Question:** Does the NAV Core abstraction actually work when we implement the first real capability?
**Dependencies:** S2 environment, API key for chosen provider.

### ⬜ S4 — Memory Persistence
**Goal:** Implement the Memory capability with a real persistence backend.
**Scope:**
- Select and integrate a storage backend (SQLite, PostgreSQL, or vector DB)
- Implement `MemoryCapabilityInterface.store()` and `retrieve()`
- Conversation context persistence across sessions
- Memory lifecycle management (creation, retrieval, expiry)
- Integration with Cognition (context-aware responses)
**Key Question:** Can NAV remember things across conversations without breaking the contract abstraction?

### ⬜ S5 — Research Capability
**Goal:** Implement the Research capability for external information discovery.
**Scope:**
- Web search integration (API-based, not scraping)
- Result extraction and synthesis
- Source attribution and citation
- Research query routing through the AI layer
- Integration with Memory (storing research results)
**Key Question:** Can NAV discover and synthesize external information through the same capability pipeline?

### ⬜ S6 — Voice Interface
**Goal:** Implement the voice-first interface with STT and TTS.
**Scope:**
- Speech-to-text integration (e.g., Whisper, browser API)
- Text-to-speech output (e.g., edge-tts, ElevenLabs)
- Audio capture and playback pipeline
- Voice command parsing and routing
- Fallback to text interface
**Key Question:** Can NAV operate as a voice-first system while maintaining the same Core pipeline?

### ⬜ S7 — Hybrid AI Routing
**Goal:** Implement the full hybrid AI routing strategy.
**Scope:**
- Local model support (Ollama/Llama)
- Free-tier API integration
- Paid frontier API integration
- Routing policy engine (complexity, cost, latency, privacy)
- Fallback chains and cost caps
**Key Question:** Can NAV intelligently route requests across multiple AI providers based on context?

### ⬜ S8 — Security Hardening
**Goal:** Implement the security enforcement plane.
**Scope:**
- Authentication and authorization
- API key management and rotation
- Sandboxed tool execution
- Privacy controls and data classification
- Audit logging
**Key Question:** Can NAV enforce security boundaries without degrading capability performance?

---

## Post-v0 Vision

After v0 capabilities are proven, future versions may explore:

- Multi-user support
- Plugin/extension system
- Mobile and desktop interfaces
- Real-time streaming responses
- Autonomous agent orchestration
- Self-improvement and meta-cognition loops

---

## Principles Guiding the Roadmap

1. **One capability per sprint.** Prove each layer before stacking the next.
2. **Contracts first.** Never break the Core abstraction to shortcut implementation.
3. **Incremental complexity.** Each sprint adds one dimension of real behavior.
4. **Document everything.** Every sprint produces a completion report.
5. **No premature optimization.** Solve the current sprint's problem, not the next one.