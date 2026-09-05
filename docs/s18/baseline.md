
S18 Baseline
Captured immediately after git checkout -b sprint/s18-human-control v1.7.

Git
Baseline tag: v1.7
Baseline commit: 2961b94
Working branch: sprint/s18-human-control
### Test suite
```text
458 passed, 1 skipped, 2 deselected in 33.04s
```

### Ruff
```text
All checks passed!
```

### Mypy
```text
tests\test_s17_work.py:206: error: Item "None" of "WorkStep | None" has no attribute "step_id"  [union-attr]
tests\test_s17_work.py:505: error: Item "None" of "WorkPlan | None" has no attribute "steps"  [union-attr]
Found 2 errors in 1 file (checked 135 source files)
```
Both mypy errors are pre-existing in S17 test code (union-attr on
narrowed types). They are non-blocking for release but S18 will clean
them up in Phase 2 so the sprint ships with a clean type baseline.

### Files inspected during recon
- `core/contracts/work.py`
- `capabilities/work/service.py`
- `capabilities/work/planner.py`
- `capabilities/work/evaluator.py`
- `capabilities/work/repository.py`
- `capabilities/work/sqlite_repo.py`
- `capabilities/work/capability.py`
- `core/orchestration/orchestrator.py`
- `tests/test_s17_work.py`

### Not inspected (deferred per charter §27):
- context managers (used only through existing contracts)
- research / memory / cognition internals (accessed only via Orchestrator)
