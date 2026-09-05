# S16 Baseline

- **Version:** v1.5
- **Commit:** 1ac53c9
- **Branch:** sprint/s16-investigation-continuity
- **Tests:** 379 passed, 1 skipped, 2 deselected
- **Ruff:** All checks passed
- **Mypy:** Success: no issues found in 80 source files

## Key S15 artifacts
- `capabilities/research/investigation/models.py` — Investigation, Hypothesis, InvestigationQuery
- `capabilities/research/investigation/service.py` — InvestigationService (standalone)
- `capabilities/research/investigation/sqlite_repo.py` — SQLiteInvestigationRepository
- `capabilities/research/investigation/repository.py` — InvestigationRepository ABC
- `capabilities/research/continuity.py` — S10 session-level continuity (NOT investigation-level)
- `tests/test_s15_investigation.py` — 379 passing tests
