# S15 Architectural Change Notes

## Change Type: Purely Additive

S15 introduces no breaking changes. All modifications are new files
and new exports.

## New Dependencies

```text
capabilities/research/investigation/
    → core.contracts.research (ResearchFinding, ResearchSource, etc.)
    → core.contracts.context (NavContext, PersonalContext)
    → core.log
```

No new external dependencies. Uses only stdlib `sqlite3`, `json`,
`uuid`, `dataclasses`.

## Dependency Direction

```text
investigation/service.py          → investigation/repository.py
investigation/service.py          → investigation/models.py
investigation/sqlite_repo.py      → investigation/models.py
investigation/sqlite_repo.py      → core.contracts.research
capabilities/research/__init__.py → investigation/ (re-exports)
```

No circular dependencies. No capabilities → core violations.
The investigation sub-package depends on core contracts and its
own models, consistent with the existing architecture.

## Data Flow

```text
User request
    → Orchestrator
    → ResearchCapability
    → ResearchService.execute_research()
        → ResearchResult
    → InvestigationService.conduct_research()
        → merges ResearchResult into Investigation
    → InvestigationRepository.update()
        → SQLite persistence
```

## Persistence

Investigations are stored in `data/nav_investigations.db` (default),
separate from `data/nav_memory.db`. This preserves the separation
between working investigation state and long-term memory.
