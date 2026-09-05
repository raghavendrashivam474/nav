# S15 Implementation Notes

## Package Structure
capabilities/research/investigation/
init.py — re-exports
models.py — Investigation, Hypothesis, enums, query
repository.py — InvestigationRepository ABC
sqlite_repo.py — SQLiteInvestigationRepository
service.py — InvestigationService

text


## Key Design Decisions

1. **Frozen dataclasses everywhere** — consistent with the rest of NAV.
   Mutations produce new instances via `dataclasses.replace()`.

2. **JSON data blob** — complex nested objects (findings, sources,
   evidence, hypotheses) are serialised into a single `data` column.
   Queryable fields (status, project_id, tags) get dedicated columns.
   This avoids complex multi-table joins while preserving full
   reconstruction fidelity.

3. **Deduplication on merge** — `conduct_research()` deduplicates
   sources by `source_id`, evidence by `evidence_id`, findings by
   `statement` text, and open questions by exact match.

4. **No contract changes** — all existing contracts, services, and
   tests remain untouched. S15 is entirely additive.

5. **ResearchService is optional** — InvestigationService accepts
   an optional research_service parameter. If not provided,
   `conduct_research()` raises RuntimeError. This keeps the
   investigation layer usable for manual curation workflows.

## Context Integration

`create_from_context()` accepts a `NavContext` and derives:
- `project_id` from `personal_context.current_focus.project_id`
- `goal_id` from `personal_context.current_focus.goal_id`
- `tags` from active project names and focus topics

This is read-only: context is never mutated.
