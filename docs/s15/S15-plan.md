# S15 Plan — Research Partner

## Mission

Introduce persistent research investigations to NAV, transforming
research from single-shot queries into ongoing collaborative
investigations.

## Scope

### In Scope
- Investigation model (identity, objective, evidence, reasoning, uncertainty)
- Investigation lifecycle (new -> active -> paused -> completed)
- Investigation persistence (SQLite, following existing patterns)
- Evidence/provenance tracking (findings linked to sources)
- Contradiction and hypothesis representation
- Open question tracking
- Follow-up research on existing investigations
- Context-informed investigation creation

### Out of Scope
- Knowledge graphs, vector databases
- Autonomous research agents
- Frontend/UI
- Memory or context rewrites
- Distributed infrastructure

## Implementation Approach

Entirely additive. No existing contracts change.

### New Structure
capabilities/research/
+-- existing files (unchanged)
+-- investigation/
+-- init.py
+-- models.py
+-- service.py
+-- repository.py
+-- sqlite_repo.py

text


### Key Design Decisions
1. Investigation is a first-class persistent entity
2. Findings reuse existing ResearchFinding/ResearchSource models
3. SQLite persistence follows SQLiteMemoryRepository pattern
4. InvestigationService composes with ResearchService
5. Context informs research but research doesn't mutate context
