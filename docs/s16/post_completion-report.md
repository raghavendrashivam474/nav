---

# S16 Post-Completion Report — Investigation Continuity

**To:** Senior Developer
**From:** Junior Developer
**Date:** 2026-09-05
**Release:** v1.6 (tag `v1.6`, commit `f60815e`)
**Baseline:** v1.5 (commit `1ac53c9`)
**Branch:** `sprint/s16-investigation-continuity` (merged and deleted)

---

## 1. Executive Summary

S16 introduces **Investigation Continuity** — the capability for NAV to meaningfully resolve, reconstruct, and resume persistent research investigations across separated sessions. Where S15 gave NAV a durable intellectual workspace (the `Investigation` primitive), S16 teaches NAV not to lose its place inside that workspace.

The implementation is fully additive, backward compatible with all S1–S15 artifacts, and introduces no new infrastructure dependencies (no LLM summarization layer, no vector database, no knowledge graph, no Orchestrator rewrite).

**Final metrics:**
- 405 tests passed, 1 skipped, 2 deselected
- Ruff: all checks passed
- Mypy: success, no issues found in 83 source files
- 15 files changed, +1,097 / −26 lines
- 5 atomic commits on the sprint branch

---

## 2. Problem Statement

S15's own post-completion report identified the central gap:

> `InvestigationService` is currently standalone and not yet wired into the Orchestrator.

More fundamentally, S15 answered *"Can an investigation exist persistently?"* but left unanswered *"Can NAV understand and resume an existing investigation later?"*

A database lookup alone is insufficient. When a user returns after days and says *"continue our local AI investigation,"* NAV needs to:

1. Identify which investigation the user means
2. Reconstruct its intellectual state (what was learned, what remains uncertain, what was last explored)
3. Present that state to the user
4. Let the user choose a direction
5. Continue research into the **same** investigation

S16 solves this without introducing autonomous decision-making. The governing principle remains: **suggest, never silently substitute.**

---

## 3. What Was Built

### 3.1 Activity Tracking (Temporal Continuity)

**Files modified:** `models.py`, `sqlite_repo.py`, `service.py`, `__init__.py`

Added an `ActivityType` enum and `InvestigationActivity` dataclass to the Investigation model:

```
ActivityType
├── RESEARCH_CONDUCTED
├── FINDING_ADDED
├── HYPOTHESIS_ADDED
├── HYPOTHESIS_UPDATED
├── QUESTION_ADDED
├── QUESTION_RESOLVED
└── STATUS_CHANGED
```

Every mutation method in `InvestigationService` now appends an `InvestigationActivity` entry via a private `_record_activity()` helper. This distinguishes meaningful research progress from incidental metadata changes (e.g., tag edits), which was the key gap identified during recon — `updated_at` alone cannot tell you what was *last explored*.

The `activity_log` field defaults to an empty tuple, making it fully backward compatible. Old S15-era investigations without activity records deserialize cleanly.

### 3.2 Continuity Subpackage (Resolution + Reconstruction)

**New directory:** `capabilities/research/investigation/continuity/`

Three files:

**`models.py`** — Defines:
- `InvestigationContinuation`: a deterministic snapshot containing progress summary, established findings, active hypotheses, contradictions, uncertainties, open questions, recent activity, and suggested directions. This is a *derived* representation, never persisted separately.
- `ResolutionMatch`: a scored candidate from investigation resolution.
- `ResolutionResult`: the outcome of resolution, carrying a confidence level (`high` / `medium` / `low` / `none`) and an ambiguity note when multiple investigations match.

**`service.py`** — `InvestigationContinuityService` with three methods:
- `resolve_investigation()`: deterministic scoring against title, objective, tags, project, goal, and status. Exact ID match short-circuits. Ambiguous matches (within 80% of top score) are surfaced rather than silently selected. No-match cases return explicit `"none"` confidence.
- `build_continuation()`: reconstructs an `InvestigationContinuation` snapshot from a loaded `Investigation`. Entirely deterministic — no LLM calls.
- `resume()`: convenience method combining resolve + reconstruct in one step.

**`__init__.py`** — Clean public exports.

### 3.3 Test Suite

**New file:** `tests/test_s16_investigation_continuity.py` (26 tests across 7 test classes)

Coverage includes:
- Activity logging for every mutation type (research, hypothesis add/update, finding, question add/resolve, status change)
- Activity log persistence round-trip
- Exact ID resolution, title substring matching, no-match, ambiguous matches, project fallback, empty database
- Continuation snapshot construction (findings, hypotheses, conflicts, recent activity, empty activity)
- Immutability guarantee (building a continuation does not mutate the investigation)
- Resume success, resume no-match, resume ambiguity
- Continue-after-resume (research updates the same investigation)
- Backward compatibility (S15-era investigations without activity_log, core S15 CRUD operations)

---

## 4. Architectural Decisions

### 4.1 Continuity as a Separate Subpackage

The continuity logic lives in `investigation/continuity/`, not merged into `InvestigationService`. This preserves the clean separation:

```
InvestigationService     → manages investigation lifecycle
ContinuityService        → resolves and reconstructs investigation state
```

The `ContinuityService` depends on `InvestigationRepository` (read access) but does not own mutation. Mutations still flow through `InvestigationService`.

### 4.2 Deterministic Resolution (No LLM, No Vector Search)

Investigation matching uses weighted scoring against structured fields:

| Signal | Weight |
|--------|--------|
| Exact title match | 0.60 |
| Title substring | 0.40 |
| Objective text | 0.20 |
| Tag match | 0.15 each |
| Project match | 0.15 |
| Goal match | 0.10 |
| Active status bonus | 0.05 |

This is cheap, testable, deterministic, and hallucination-free. Vector search and LLM-based matching are explicitly deferred.

### 4.3 Derived Snapshots, Not Competing Sources of Truth

The `InvestigationContinuation` is computed on demand from the `Investigation`. It is never persisted. This avoids the duplication trap of maintaining parallel state objects that drift out of sync.

### 4.4 Activity Log in the JSON Blob

Rather than adding a new SQLite table or schema migration, `activity_log` is serialized into the existing `data` JSON column alongside hypotheses, findings, sources, etc. This keeps the schema unchanged and old records backward compatible.

### 4.5 No Orchestrator Integration

S15 deliberately left `InvestigationService` standalone. S16 continues this pattern — the continuity service layer is ready for integration, but wiring it into the Orchestrator or `ResearchCapability` is deferred to a future sprint. This avoids destabilizing the existing routing and session management.

---

## 5. Backward Compatibility

| Artifact | Status |
|----------|--------|
| `InvestigationRepository` interface | Unchanged |
| `InvestigationService` public API | Unchanged (signatures, return types) |
| SQLite schema | Unchanged (activity_log in JSON blob) |
| `ResearchService` | Untouched |
| `ResearchCapability` | Untouched |
| `ResearchContinuityResolver` (S10) | Untouched |
| `NavContext` / `PersonalContext` | Untouched |
| Memory system | Untouched |
| Orchestrator | Untouched |
| All S1–S15 tests | 379 original tests still pass |

Old investigations created under S15 (without `activity_log`) deserialize to an empty tuple and produce a continuation with `"No recorded activity."` — verified by test.

---

## 6. What Was Deliberately Not Built

| Item | Reason |
|------|--------|
| LLM-generated investigation summaries | Deterministic reconstruction is sufficient, cheaper, and testable. Summarization can layer on top later. |
| Orchestrator wiring | Service layer first; integration is a separate concern. |
| Vector similarity search | Deterministic scoring handles current scale. |
| Cross-investigation knowledge graph | Out of scope; S17 territory. |
| Autonomous research loops | Violates "suggest, never silently substitute." |
| Frontend / Voice UI changes | S19. |
| Memory or Context redesign | Clean separation maintained; no justification for coupling. |
| Full event-sourcing system | Activity log in JSON blob is sufficient; event sourcing would be over-engineering at this scale. |

---

## 7. Git History

```
f60815e merge(s16): Investigation Continuity (v1.6)
ce0c492 docs(s16): add implementation, change notes, and completion reports
d1ce008 test(s16): add investigation continuity and activity tracking test coverage
d906473 feat(research): add investigation continuity models and service
35fa5b3 feat(research): add investigation activity tracking and backward-compatible persistence
52332c1 docs(s16): add recon, baseline, and sprint plan
1ac53c9 merge(s15): Research Partner — Persistent Investigations (v1.5)
```

Five capability-scoped commits, clean merge to `main`, tagged `v1.6`, sprint branch deleted.

---

## 8. Foundation for S17

S16 provides S17 (Technical Intelligence) with:

1. **A reliable activity history** — the `activity_log` gives S17 a provenance-preserving timeline of what was explored and when, without depending on LLM-generated summaries.
2. **A resolution primitive** — S17 can use `resolve_investigation()` to connect incoming intelligence queries to existing investigation threads.
3. **A continuation snapshot** — S17 can consume `InvestigationContinuation` to understand the current intellectual state of any investigation without re-deriving it.
4. **Clean architectural boundaries** — the separation between `InvestigationService` (mutation) and `ContinuityService` (read/reconstruct) gives S17 a stable integration surface.

---

## 9. Open Items for Future Sprints

- Orchestrator integration: wiring `ContinuityService` into the request routing pipeline so that user utterances like *"continue our X investigation"* automatically resolve and resume.
- AI-generated investigation summaries: a replaceable LLM layer on top of the deterministic snapshot, for more natural conversational output.
- Cross-investigation search and linking.
- Automatic archival of completed investigations.

---

**S16 is complete. Release `v1.6` is tagged and pushed.**