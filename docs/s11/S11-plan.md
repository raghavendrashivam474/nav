# S11 Sprint Plan — Foundation & v1 Architecture

**Baseline:** v0.10 (`2e0e706`)
**Target:** v1.1
**Branch:** `sprint/s11-foundation`
**Status:** In progress — Phase 1 complete (recon)

---

## Sprint principle

> Do not redesign NAV because you can. Evolve NAV because the North Star requires it.

---

## Phase gate summary

| Phase | Deliverable | Status |
|---|---|---|
| P0 | Baseline verification | ✅ Done |
| P1 | Repository reconnaissance | ✅ Done |
| P2 | Baseline audit published | ⏳ In progress |
| P3 | v1 target architecture document | ⏳ Pending |
| P4 | Architecture Decision Records (Q1–Q4) | ⏳ Pending |
| P5 | External integration contract (Avni) | ⏳ Pending |
| P6 | Minimal additive code changes | ⏳ Pending |
| P7 | Tests + lint + typecheck clean | ⏳ Pending |
| P8 | Completion report + tag `v1.1` | ⏳ Pending |

---

## P3 — v1 Target Architecture Document

Location: `docs/architecture/v1-architecture.md`

Must specify, with reference to the audit:

- Core boundary (what belongs, what does not)
- Runtime concept (documented, not necessarily implemented)
- Capability model (verified against current implementation)
- Provider/Adapter model
- Context Manager (contract-only for S11)
- Persistence categories (ephemeral, session, long-term)
- Identity boundary
- Security boundary (contract-only; implementation deferred to S20)
- External integration model (Avni as concrete example)
- Dependency direction (must match §8 of the audit)

---

## P4 — Architecture Decision Records

Location: `docs/architecture/decisions/`

Required ADRs:

- **ADR-001:** Voice remains a frontend, not a capability (resolves Q1)
- **ADR-002:** Core/Runtime distinction documented, not implemented (resolves Q2)
- **ADR-003:** ContextManager contract lives in `core/context/`; capabilities register their own stores (resolves Q3)
- **ADR-004:** External systems integrate as providers, not as embedded packages (resolves Q4)
- **ADR-005:** Security enforcement plane is deferred to S20; per-capability defenses remain valid in the interim

---

## P5 — External Integration Contract

Location: `docs/architecture/external-integration.md`

Content:

- The provider model as the single external integration seam
- Avni as concrete example: implements `SpeechToText` and/or `TextToSpeech`
- Transport is an adapter concern (HTTP, gRPC, IPC — not prescribed)
- NAV never imports external system internals
- External systems never import NAV internals

---

## P6 — Minimal Additive Code Changes

Scope (from audit §10):

1. `core/contracts/__init__.py` — add re-exports for `Request`, `Response`, `Capability`, `NavContext`, etc. Zero behavior change.
2. `core/context/` — add `context_manager.py` with a `ContextManager` ABC (contract only, no implementation logic beyond a stub).
3. Verify `ai/router/` is truly redundant with `ai/routing/`; if so, remove. Otherwise document why both exist.

**Nothing else touched in P6.**

---

## P7 — Verification

- `pytest -q` — all tests pass, no regressions
- `ruff check .` — clean
- `ruff format --check .` — clean
- `mypy core/ ai/ capabilities/cognition/ capabilities/memory/ capabilities/research/ interfaces/voice/ security/` — clean
- New tests for `ContextManager` contract (contract-level tests only)

---

## P8 — Completion

- Write `docs/sprints/s11/completion-report.md`
- Squash-clean commit history if needed
- Final commit → push to `sprint/s11-foundation`
- Open PR / fast-forward merge to `main`
- Verify `main == origin/main`
- Verify clean tree
- Tag `v1.1`
- Push tag
- 🔒 S11 CLOSED

---

## Explicit non-goals

Per brief §27, S11 does **not** deliver:

- Personal context implementation
- Knowledge graph
- Full security plane
- Wake-word / continuous voice
- Autonomous agent behavior
- New capabilities
- Frontend
- Database migration
- Microservices
- Cloud infrastructure

---

*End of plan.*
