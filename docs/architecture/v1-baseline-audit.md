# NAV v1 Baseline Audit

**Sprint:** S11 — Foundation & v1 Architecture
**Phase:** Reconnaissance (no code changes)
**Baseline:** v0.10 (commit `2e0e706`)
**Author:** S11 architecture audit
**Status:** Draft 1 — grounded in actual repository inspection

---

## 1. Purpose

Before proposing any architectural change for NAV v1, this document records
what NAV **actually is** as of v0.10, not what it was assumed to be. Every
finding below was verified by reading the source, not from memory or from
the sprint brief.

The audit answers three questions:

1. What is the current architecture?
2. Where does it already do the right thing?
3. Where does it genuinely limit NAV v1?

Nothing in this document authorizes refactoring. It only enables the S11
architectural design phase to be honest.

---

## 2. Actual Repository Layout

```text
NAV/
├── core/
│   ├── contracts/          # capability, ai, memory, research, context
│   ├── capabilities/       # registry only (not the capabilities themselves)
│   ├── orchestration/      # orchestrator (pass-through router)
│   ├── context/            # EMPTY (__init__.py is 0 bytes)
│   ├── log.py
│   └── __init__.py         # empty
│
├── ai/                     # Top-level AI infrastructure (NOT under core/)
│   ├── gateway/            # DefaultAIGateway
│   ├── providers/          # ollama, openai
│   ├── routing/            # ModelRouter, RoutingContext, ProviderMetadata
│   ├── policies/           # (present, minimal)
│   ├── router/             # (present, minimal — appears redundant with routing/)
│   └── errors.py
│
├── capabilities/
│   ├── cognition/          # CognitionCapability
│   ├── memory/             # capability + service + repository + sqlite_repo
│   └── research/           # 14+ files, own providers, own cache, own security
│
├── interfaces/
│   └── voice/              # VoiceInterface (NOT a Capability — see F2)
│       ├── stt/            # whisper, mock
│       └── tts/            # pyttsx3, mock
│
├── security/               # PLACEHOLDER (__init__.py is 0 bytes)
├── tests/
├── scripts/
├── data/
└── docs/
    └── s10/                # existing sprint docs
Key structural facts (verified)
core/ contains contracts, registry, orchestrator, and an empty context module.
ai/ is a top-level package, not under core/. This is intentional: AI is shared infrastructure consumed by multiple capabilities.
capabilities/ contains cognition, memory, research — but not voice.
interfaces/voice/ is the voice frontend. It is not a Capability and does not appear in CapabilityRegistry.
security/ exists as a package but is empty.
core/context/ exists as a package but is empty.
3. Contract Surface (Verified)
3.1 Core contracts (core/contracts/)
File    Defines    Notes
capability.py    Capability ABC, Request, Response    Payload/data are untyped dict[str, Any]
context.py    UserContext, SessionContext, ConversationContext, ResearchSessionContext, NavContext    S10 added ResearchSessionContext; all frozen dataclasses
ai.py    AIGateway ABC, AIRequest, AIResponse, AIMessage    Clean; routing hints passed via options["routing"]
memory.py    MemoryCapabilityInterface, MemoryRecord, MemoryQuery    Full CRUD (store/retrieve/update/forget)
research.py    ResearchCapabilityInterface, plus 10+ dataclasses and 2 Protocols    Most complex contract in the system
__init__.py    empty — no re-exports    Every import uses deep paths
3.2 Capability implementations
Every capability implements the same dual-inheritance pattern:

Python

class MemoryCapability(Capability, MemoryCapabilityInterface): ...
class ResearchCapability(Capability, ResearchCapabilityInterface): ...
class CognitionCapability(Capability):  # no separate interface — cognition IS the capability
This lets each capability be routed via Orchestrator (via invoke) or used directly by another capability (via its typed interface). This is genuinely a good pattern and should be preserved.

3.3 Voice contracts (interfaces/voice/contracts.py)
SpeechToText ABC
TextToSpeech ABC
Concrete providers: whisper_stt, mock_stt, pyttsx3_tts, mock_tts
Voice contracts live under interfaces/, not core/contracts/. This is a deliberate signal: voice is treated as a UI/frontend concern, not a capability contract.

4. Runtime Behavior (Verified)
4.1 Orchestrator
Python

def route_request(self, target_capability, request):
    capability = self.registry.get(target_capability)
    return capability.invoke(request)
That is the entire orchestrator. It:

has no context injection
has no policy hooks
has no observability beyond logger.error on exception
has no session awareness
has no middleware
is fully synchronous
Wiring (registry construction, provider selection, capability instantiation) is done in demo scripts, not by a runtime.

4.2 AI Gateway (ai/gateway/default_gateway.py)
DefaultAIGateway:

registers Ollama and (conditionally) OpenAI providers at init
extracts routing hints from AIRequest.options["routing"]
delegates to ModelRouter for provider selection
executes with a fallback chain
re-enforces hard constraints (e.g., local_only) on fallback candidates
This is a mature, well-designed subsystem. It is arguably the most complete piece of infrastructure in NAV and should serve as the reference model for other capability areas.

4.3 VoiceInterface (interfaces/voice/interface.py)
VoiceInterface:

captures audio via MicrophoneProtocol
transcribes via SpeechToText
constructs a Request and routes through Orchestrator (always as cognition)
speaks the reply via TextToSpeech + SpeakerProtocol
tracks _active_session_id across turns (S10 addition)
Critical: it hard-codes capability = "cognition". Voice never invokes memory or research directly; it always goes through cognition. Research continuity works because cognition returns a session_id that voice remembers.

4.4 Research capability
The most sophisticated subsystem. Owns:

context_store.py — thread-safe in-memory session store
continuity.py — regex-based intent resolver
cache.py — TTL discovery cache
concurrency.py — parallel retrieval
providers/ — brave, duckduckgo, router
security.py — prompt-injection defense local to research
progress.py — voice progress reporting
service.py — orchestration of the research pipeline
Research is almost a subsystem within NAV. This is fine for now, but note that security concerns are being solved per-capability instead of by a shared plane (see D9).

5. Findings — Architectural Strengths (KEEP)
ID    Strength    Evidence
S1    Contract-first design is real    Every capability implements an ABC; providers implement Protocols
S2    AI as top-level infrastructure    ai/ correctly sits beside core/ and capabilities/, not inside either
S3    Dual-inheritance pattern    Capability + <XxxInterface> allows both orchestrated and direct use
S4    Provider abstraction is proven    Works in AI (ollama/openai) and Research (brave/duckduckgo)
S5    Repository pattern in Memory    MemoryRepository + SqliteMemoryRepository — persistence is already abstracted
S6    Frozen dataclasses everywhere    Immutability is enforced across contracts
S7    Session/memory distinction is explicit    ResearchSessionContext documented as "volatile, NOT long-term memory"
S8    Backward-compatible additive evolution    S10 added ResearchSessionContext without breaking any S1–S9 contract
S9    Router + fallback chain in AI    ModelRouter + DefaultAIGateway._execute_with_fallback is a strong pattern
S10    Voice is decoupled from cognition    Voice is a frontend, not a capability — good separation
6. Findings — Architectural Debt (IMPROVE / RESEARCH)
ID    Debt    Evidence    Severity    v1 Impact
D1    core/context/ is empty    core/context/__init__.py is 0 bytes    HIGH    v1 needs a real context manager for personal context, sessions, identity
D2    Voice is not routed through a capability boundary    VoiceInterface hard-codes capability = "cognition" and constructs Request directly    HIGH    Brief's "Voice Capability → Avni Adapter" model doesn't fit current architecture
D3    Orchestrator is a pass-through    route_request is 3 lines    MEDIUM    v1 needs context injection, policy hooks, observability
D4    Request/Response payloads are untyped dicts    Every capability re-parses payload["prompt"], payload["question"], payload["action"]    MEDIUM    External integrations (Avni) will make this pain worse
D5    Session state lives inside capabilities    ResearchContextStore lives in capabilities/research/    MEDIUM    Cross-capability context (e.g., voice + research) requires ad-hoc coordination
D6    No Runtime layer    Wiring happens in demo scripts    MEDIUM    v1 needs a defined entry point for NAV as a system
D7    Cognition duplicates intent detection    Regex _is_remember / _is_forget in cognition, similar patterns in research continuity    LOW    Not a blocker, but suggests a missing intent-classification boundary
D8    Empty core/contracts/__init__.py    No re-exports; imports are verbose    LOW    Easy fix, deferrable
D9    Security is per-capability, not a plane    capabilities/research/security.py implements prompt-injection defense locally; security/ is empty    MEDIUM    Brief §15 says security must be an "independent enforcement plane"
D10    ai/routing/ and ai/router/ both exist    Suggests earlier refactor left a stub behind    LOW    Cleanup opportunity
D11    Voice hard-couples to cognition    VoiceInterface(capability="cognition") — voice cannot route to research directly    MEDIUM    Blocks direct voice→research invocation
D12    No cross-capability event bus    Capabilities cannot notify each other; all coordination is request/response    LOW-MEDIUM    Deferrable; only matters if v1 needs async cross-cap flows
7. Architectural Ambiguities (RESEARCH)
These are open questions the S11 design phase must answer explicitly.

Q1: Is voice a capability, a frontend, or both?
Current answer: frontend that consumes cognition.
Brief's assumption: voice is a capability (Voice Capability → Avni Adapter).
Tension: if voice becomes a capability, cognition-through-voice needs a redesign. If voice stays as a frontend, Avni integration happens at the STT/TTS provider level, not at a capability level.
Recommendation for S11: treat STT/TTS as the extensible boundary (Avni as an STT+TTS provider), keep VoiceInterface as a frontend. Do not turn voice into a Capability unless a concrete v1 need requires it.
Q2: What belongs in Core vs. a Runtime?
Current answer: no distinction exists. core/ contains contracts + registry + orchestrator, and the "runtime" is whatever wiring code the demo scripts do.
Options:
(a) Promote demo wiring into a real runtime/ package.
(b) Keep everything in core/ and just add a bootstrap module.
(c) Defer — S11 documents the concept but doesn't implement it.
Recommendation for S11: option (c) — document the Core/Runtime distinction and only extract runtime if v1 work in later sprints actually needs it. Avoid premature layering.
Q3: Where does personal/session/user context live?
Current answer: research owns its own context store; there is no general context manager.
Tension: Personal context (S12+) will need to span capabilities.
Recommendation for S11: design a Context Manager contract in core/context/ that:
owns the session/user identity
hosts per-capability context stores as registered subsystems
remains empty of implementation logic (contract + registry only in S11)
Q4: How does an external system like Avni integrate?
Current answer: no defined boundary. Providers (SearchProvider, AIGateway, SpeechToText, TextToSpeech, MemoryRepository) are the closest analogues.
Recommendation for S11: document the Adapter/Provider Boundary Contract:
external systems implement one or more of NAV's existing provider contracts
Avni's first concrete integration is as an STT+TTS provider under interfaces/voice/
NAV does not import Avni; Avni implements NAV interfaces
transport (HTTP, gRPC, IPC) is an adapter implementation detail
8. Dependency Direction (Verified)
Current dependency flow, from bottom (concrete) to top (abstract):

text

Providers                (openai, ollama, brave, ddg, whisper, pyttsx3, sqlite)
    ↓ implement
Contracts / Protocols    (AIGateway, SearchProvider, SpeechToText, MemoryRepository, ...)
    ↓ used by
Capabilities             (cognition, memory, research)
    ↓ registered in
Core                     (registry, orchestrator, contracts)
    ↑ consumed by
Interfaces               (voice)
Verified: core/ does not import from capabilities/ or ai/providers/. The dependency direction is correctly enforced today.

Risk: the empty core/context/ and empty security/ could tempt someone to reverse this direction if a capability needs "just a little bit of context state." S11 must define these boundaries before v1 features start accumulating.

9. Classification Summary
Category    Count    Notes
KEEP    10 (S1–S10)    Preserve without modification
IMPROVE    6 (D3, D4, D5, D6, D9, D11)    Address during S11 or explicitly defer with justification
DEFER    3 (D8, D10, D12)    Low-impact; deferrable to later sprints
RESEARCH    4 (Q1–Q4)    Must be resolved during S11 design phase
BLOCKING for v1    2 (D1, D2)    Must be addressed before v1 personal-context work begins
10. Recommended Scope for S11 Implementation
Based on this audit, the S11 implementation phase should be limited to:

Must-do (documentation only, S11 core deliverable)
Publish this audit.
Publish docs/architecture/v1-architecture.md — the target v1 architecture document.
Publish ADRs for each RESEARCH question (Q1–Q4).
Publish docs/architecture/external-integration.md — the Avni-and-beyond integration model.
Should-do (minimal, additive code changes)
Populate core/contracts/__init__.py with re-exports (D8) — trivial cleanup.
Add a ContextManager contract only in core/context/ — no implementation logic. Just the interface that future sprints will implement.
Remove the stub ai/router/ package if confirmed redundant (D10) — verify first.
Explicitly deferred (with justification)
D2 (voice-as-capability): deferred to a future sprint. S11 documents Avni as an STT/TTS provider, which is the correct integration seam given current architecture.
D3 (orchestrator middleware): deferred. Add only when a concrete v1 feature requires it.
D4 (typed request/response): deferred. Migration cost is high; benefit is speculative until we see external integration pain.
D9 (security plane): deferred to S20 per brief. S11 documents where it belongs.
D12 (event bus): deferred. Not needed until an actual async cross-cap flow is designed.
Explicitly forbidden in S11
Rewriting Core.
Turning voice into a capability.
Moving capabilities/research/context_store.py into core (design the contract first; move only when the second capability needs it).
Replacing SQLite / Ollama / Whisper / pyttsx3.
Introducing a message broker, database migration, or async framework.
11. Next Step
Author docs/architecture/v1-architecture.md — the target v1 architecture, informed by this audit.
Then author ADRs for Q1–Q4.
Then, and only then, make the minimal additive code changes listed in §10.

End of audit.
