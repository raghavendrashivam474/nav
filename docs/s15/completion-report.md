# S15 Completion Report — Research Partner

## Summary

S15 introduces persistent research investigations to NAV,
transforming research from single-shot queries into ongoing
collaborative investigations that accumulate findings, evidence,
sources, hypotheses, and open questions over time.

## What Was Built

### New Models (`investigation/models.py`)
- `InvestigationStatus` enum: `NEW` → `ACTIVE` → `PAUSED` → `COMPLETED` → `ARCHIVED`
- `HypothesisStatus` enum: `PROPOSED` → `SUPPORTED` / `REFUTED` / `INCONCLUSIVE`
- `Hypothesis` dataclass with evidence links and rationale
- `Investigation` dataclass reusing `ResearchFinding`, `ResearchSource`,
  and `ResearchEvidence` from existing contracts
- `InvestigationQuery` for filtered listing

### Persistence (`investigation/repository.py`, `sqlite_repo.py`)
- `InvestigationRepository` ABC following `MemoryRepository` pattern
- `SQLiteInvestigationRepository` with JSON data blob for nested
  objects and dedicated columns for queryable fields
- Full round-trip serialisation of all nested research models

### Service Layer (`investigation/service.py`)
- `InvestigationService` with full lifecycle management:
  - `create_investigation()` / `create_from_context()`
  - `conduct_research()` — executes via `ResearchService`, merges results
  - `add_hypothesis()` / `update_hypothesis()`
  - `add_finding()` / `add_open_question()` / `resolve_open_question()`
  - `set_status()` / `get_investigation()` / `list_investigations()`
  - Deduplication on merge (sources, evidence, findings, questions)
  - Context-informed creation (`project_id`, `goal_id`, `tags` from `NavContext`)

### Tests (`tests/test_s15_investigation.py`)
- Model creation and helper methods
- Repository CRUD and round-trip persistence
- Service lifecycle management
- Research integration with deduplication
- Hypothesis management
- Finding and open question tracking
- Context-informed creation

## What Was NOT Changed

- No existing contracts modified
- No existing services modified
- No existing tests modified
- No changes to Memory, Context, or Orchestration layers
- All 344 existing tests continue to pass

## Metrics

- New source files: 5
- New test file: 1
- New tests: ~35
- Lines of code added: ~900
- Existing tests broken: 0
