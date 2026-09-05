---

# S15 Post-Completion Report — Research Partner

**To:** Senior Development Lead
**From:** NAV Development Team
**Date:** 2026-09-05
**Branch:** `sprint/s15-research-partner`
**Base:** `v1.4` (commit `ab4a50b`)
**Head:** commit `25ebb33`

---

## 1. Executive Summary

Sprint 15 introduces **persistent research investigations** to NAV, transforming the research capability from a stateless, single-shot query engine into a system that supports ongoing, multi-session collaborative investigations. Investigations accumulate findings, evidence, sources, hypotheses, and open questions over time, backed by SQLite persistence.

The entire sprint was implemented **additively** — zero existing contracts, services, or tests were modified in any functional way. All 344 pre-existing tests continue to pass unchanged alongside 35 new tests.

---

## 2. Problem Statement

Prior to S15, NAV's research capability (`ResearchService.execute_research()`) was **fire-and-forget**: a user asked a question, NAV returned findings and sources, and the entire result was discarded when the interaction ended. This meant:

- **No accumulation of knowledge** across related research sessions.
- **No hypothesis tracking** — NAV could not propose, test, or refute propositions over time.
- **No investigation lifecycle** — there was no concept of an investigation being "in progress," "paused," or "completed."
- **Lost provenance context** — even when findings were optionally saved to Memory (S9), the structural relationships between sources, evidence, and findings were flattened.
- **No contradiction tracking across sessions** — S13's `detect_contradictions()` operated on Memory records, not on structured research findings.

S15 addresses all of these gaps without disrupting the existing research pipeline.

---

## 3. Architecture & Design Decisions

### 3.1 Package Structure

```
capabilities/research/
    __init__.py              (updated: re-exports investigation classes)
    capability.py            (unchanged)
    service.py               (unchanged)
    ...existing files...     (all unchanged)
    investigation/           (NEW)
        __init__.py
        models.py
        repository.py
        sqlite_repo.py
        service.py
```

### 3.2 Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Frozen dataclasses everywhere** | Consistent with S1–S14 pattern. Mutations produce new instances via `dataclasses.replace()`. Thread-safe by default. |
| 2 | **JSON data blob for nested objects** | Findings, sources, evidence, and hypotheses are serialised into a single `data` column in SQLite. Queryable fields (status, project_id, tags) get dedicated columns. This avoids complex multi-table joins while preserving full reconstruction fidelity. A normalised schema can be introduced later via migration if cross-investigation queries become necessary. |
| 3 | **Reuse of existing research models** | `Investigation` directly embeds `ResearchFinding`, `ResearchSource`, and `ResearchEvidence` from `core.contracts.research`. No conversion layers, no duplication. |
| 4 | **Separate SQLite database** | Investigations persist in `data/nav_investigations.db`, distinct from `data/nav_memory.db`. This preserves the conceptual boundary: Memory is for long-term recall; Investigations are for active working state. |
| 5 | **Protocol-based ResearchService dependency** | `InvestigationService` accepts any object satisfying the `ResearchExecutor` protocol (has `execute_research()` method). This avoids circular imports (investigation lives inside research) and enables clean testing with fakes. |
| 6 | **Deduplication on merge** | `conduct_research()` deduplicates sources by `source_id`, evidence by `evidence_id`, findings by `statement` text, and open questions by exact match. Repeated research calls on the same investigation do not accumulate duplicates. |
| 7 | **Read-only context integration** | `create_from_context()` derives `project_id`, `goal_id`, and tags from `NavContext.personal_context` without mutating it. Consistent with S14's "Memory informs Context; Memory does not become Context" principle. |

### 3.3 Dependency Graph

```
investigation/service.py
    → investigation/repository.py (ABC)
    → investigation/models.py
    → core.contracts.research (ResearchQuery, ResearchResult, ResearchFinding, SupportState)
    → core.contracts.context (NavContext)

investigation/sqlite_repo.py
    → investigation/models.py
    → investigation/repository.py
    → core.contracts.research (all research data models + enums)

capabilities/research/__init__.py
    → investigation/ (re-exports)
```

No circular dependencies. No `capabilities → core` violations. No new external dependencies (stdlib only: `sqlite3`, `json`, `uuid`, `dataclasses`).

---

## 4. What Was Built

### 4.1 Models (`investigation/models.py`)

- **`InvestigationStatus`** (enum): `NEW → ACTIVE → PAUSED → COMPLETED → ARCHIVED`
- **`HypothesisStatus`** (enum): `PROPOSED → SUPPORTED / REFUTED / INCONCLUSIVE`
- **`Hypothesis`** (frozen dataclass): `hypothesis_id`, `statement`, `status`, `evidence_ids`, `rationale`, `created_at`
- **`Investigation`** (frozen dataclass): Full investigation record with `investigation_id`, `title`, `objective`, `status`, `hypotheses`, `findings`, `conflicts`, `uncertainties`, `sources`, `evidence`, `open_questions`, `tags`, `project_id`, `goal_id`, timestamps, and metadata. Includes helper methods: `sources_by_status()`, `evidence_for_source()`, `evidence_for_finding()`.
- **`InvestigationQuery`** (frozen dataclass): Filter criteria for listing — `query_text`, `status`, `tags`, `project_id`, `limit`.

### 4.2 Persistence (`investigation/repository.py`, `sqlite_repo.py`)

- **`InvestigationRepository`** (ABC): `initialize()`, `save()`, `get()`, `find()`, `update()`, `delete()`. Follows the `MemoryRepository` pattern from S6/S13.
- **`SQLiteInvestigationRepository`**: Concrete implementation with:
  - Idempotent schema creation (`CREATE TABLE IF NOT EXISTS`)
  - Full serialisation/deserialisation of all nested research models including enums (`SourceType`, `SourceStatus`, `SupportState`, `InvestigationStatus`, `HypothesisStatus`)
  - Dedicated columns for `status`, `project_id`, `goal_id`, `tags` to support filtered queries
  - JSON `data` column for complex nested structures
  - `sqlite3.Row` row factory for clean column access

### 4.3 Service Layer (`investigation/service.py`)

**`InvestigationService`** provides the full investigation lifecycle:

| Method | Description |
|--------|-------------|
| `create_investigation()` | Create a new investigation in `NEW` status |
| `create_from_context()` | Create an investigation informed by `NavContext` (derives project, goal, tags) |
| `conduct_research()` | Execute a `ResearchQuery` via `ResearchService`, merge deduplicated results, transition `NEW → ACTIVE` |
| `add_hypothesis()` | Add a proposed hypothesis to an investigation |
| `update_hypothesis()` | Update hypothesis status, evidence links, and rationale |
| `add_finding()` | Manually add a finding with evidence and support state |
| `add_open_question()` | Track an unresolved question (idempotent) |
| `resolve_open_question()` | Remove a resolved question |
| `set_status()` | Transition investigation lifecycle state |
| `get_investigation()` | Retrieve by ID |
| `list_investigations()` | Filtered listing via `InvestigationQuery` |
| `delete_investigation()` | Remove an investigation |

### 4.4 Tests (`tests/test_s15_investigation.py`)

**35 tests** across 7 test classes:

| Test Class | Count | Coverage |
|------------|-------|----------|
| `TestInvestigationModels` | 6 | Defaults, helper methods, hypothesis, query |
| `TestInvestigationRepository` | 10 | CRUD, duplicates, missing records, filtered queries, complex round-trip |
| `TestInvestigationService` | 4 | Create, get, list, delete |
| `TestInvestigationLifecycle` | 6 | Status transitions, conduct_research, merge, dedup, error handling |
| `TestInvestigationHypotheses` | 3 | Add, update status, missing hypothesis error |
| `TestInvestigationFindingsAndQuestions` | 4 | Add finding, add/resolve questions, duplicate question no-op |
| `TestInvestigationContext` | 2 | Context-informed creation with/without personal context |

### 4.5 Documentation (`docs/s15/`)

| File | Purpose |
|------|---------|
| `S15-plan.md` | Sprint scope, in/out of scope, implementation approach |
| `S15-recon-notes.md` | 17 recon questions answered about existing architecture |
| `baseline.md` | Starting metrics and architecture snapshot |
| `implementation.md` | Design decisions, data flow, context integration details |
| `completion-report.md` | What was built, what was not changed, metrics |
| `architectural_change_notes.md` | Dependency direction, data flow, persistence details |

---

## 5. What Was NOT Changed

This is critical for regression confidence:

- **Zero existing contracts modified** (`core/contracts/research.py`, `core/contracts/memory.py`, `core/contracts/context.py` — all functionally unchanged)
- **Zero existing services modified** (`ResearchService`, `MemoryService`, `ContextStore` — all untouched)
- **Zero existing tests modified functionally** (S13 test file received formatting-only changes from `ruff format`)
- **No changes to orchestration, voice, cognition, or routing layers**
- **No new external dependencies**

The only modified existing file with functional content is `capabilities/research/__init__.py`, which gained re-exports of the new investigation classes. This is a pure addition — no existing exports were removed or altered.

---

## 6. Verification Metrics

| Metric | Before S15 | After S15 | Delta |
|--------|-----------|-----------|-------|
| Total tests | 344 passed | 379 passed | +35 |
| Skipped | 1 | 1 | 0 |
| Deselected | 2 | 2 | 0 |
| Failed | 0 | 0 | 0 |
| Ruff errors | 0 | 0 | 0 |
| Mypy errors (strict) | 0 | 0 | 0 |
| Source files | 116 | 122 | +6 |
| New Python files | — | 5 | +5 |
| New doc files | — | 6 | +6 |

---

## 7. Git History

Three atomic, capability-scoped commits on `sprint/s15-research-partner`:

```
25ebb33 feat(research): add persistent investigations, hypothesis tracking, and s15 tests
7ffb1b7 docs(s15): add plan, baseline, change notes, implementation and completion reports for s15
5ea2ed7 style(formatting): clean up whitespace and formatting in memory, context, and s13 tests
```

---

## 8. Known Limitations & Future Work (S16+)

| Area | Current State | Future Direction |
|------|--------------|-----------------|
| **Orchestration integration** | InvestigationService is standalone; not yet wired into the Orchestrator | S16: Auto-create investigations from multi-turn research conversations |
| **AI-generated summaries** | Investigations store raw findings | S16: AI-generated investigation progress reports and digests |
| **Cross-investigation search** | Each investigation is isolated | S17: Cross-investigation linking, shared evidence pools |
| **Archival policies** | No automatic cleanup | S17: TTL-based archival, completed investigation compression |
| **Export/sharing** | No export mechanism | S18: Investigation export to Markdown/PDF |
| **Normalised schema** | JSON data blob for nested objects | Migrate to normalised tables + FTS index if cross-investigation queries become a bottleneck |
| **Vector similarity** | Text-based `LIKE` queries only | Deferred per S15 plan (out of scope) |

---

## 9. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| JSON blob query performance at scale | Low (current user base) | Dedicated columns for all filtered fields; blob only used for reconstruction |
| Circular import between research and investigation | Eliminated | Protocol-based typing (`ResearchExecutor`) avoids hard import |
| Data loss on schema evolution | Low | Idempotent `CREATE TABLE IF NOT EXISTS`; migration pattern proven in S13 |
| Test isolation | Eliminated | All tests use `tmp_path` fixture; no shared state |

---

## 10. Conclusion

S15 successfully delivers persistent research investigations as a first-class capability within NAV's research layer. The implementation is entirely additive, fully tested, and consistent with the architectural patterns established across S1–S14. The investigation model provides the structural foundation for NAV to evolve from a reactive research tool into a proactive research partner that accumulates and organises knowledge over time.

**Recommendation:** Merge `sprint/s15-research-partner` into `main` and tag as `v1.5`.