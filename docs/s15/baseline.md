# S15 Baseline

## Starting Point

- **Version:** v1.4
- **Commit:** ab4a50b
- **Branch:** sprint/s15-research-partner
- **Date:** 2026-09-05

## Baseline Metrics

- **Tests:** 21 passing
- **Ruff:** Clean
- **Mypy:** Clean (strict)
- **Source files:** 18

## Existing Architecture

### Research Capability
- `capabilities/research/models.py` — ResearchSource, ResearchFinding, ResearchResult
- `capabilities/research/service.py` — ResearchService (delegates to ResearchProvider)
- `core/contracts/research.py` — ResearchProvider abstract contract

### Memory
- `core/contracts/memory.py` — MemoryEntry, MemoryProvider
- `capabilities/memory/service.py` — MemoryService (semantic analysis + repo)
- `capabilities/memory/repository.py` — MemoryRepository abstract
- `capabilities/memory/sqlite_repo.py` — SQLiteMemoryRepository
- `capabilities/memory/semantics.py` — SemanticAnalyzer

### Context
- `core/contracts/context.py` — ContextSnapshot, ContextProvider
- `core/context/store.py` — ContextStore (in-memory)
- `core/context/context_manager.py` — ContextManager (with memory integration)
- `core/context/integration.py` — MemoryContextIntegration (S14)

### Orchestration
- `core/orchestration/orchestrator.py` — Routes by intent, gathers context

## Key Observations

1. Research is currently stateless — fire-and-forget
2. ResearchResult/Finding/Source models are clean and reusable
3. SQLite persistence pattern exists in memory (reusable for investigations)
4. MemoryRepository abstract pattern is a good precedent for InvestigationRepository
5. Context enrichment via memory already works (S14)
6. All boundaries are clean — additive extension is feasible
