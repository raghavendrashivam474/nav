# S17 Implementation Notes

## Architecture

S17 introduces a new **Work** subsystem under `capabilities/work/` with
contracts in `core/contracts/work.py`. The design follows the existing
NAV capability-oriented architecture:
```text
core/contracts/work.py → Work, WorkPlan, WorkStep, enums, protocols
capabilities/work/
├── repository.py → WorkRepository ABC
├── sqlite_repo.py → SQLiteWorkRepository
├── planner.py → DeterministicPlanner, AIPlanner
├── evaluator.py → DeterministicEvaluator
├── service.py → WorkService (lifecycle + execution)
└── capability.py → WorkCapability (Orchestrator integration)
```


## Key Design Decisions

### 1. Frozen Dataclasses
All models (`Work`, `WorkPlan`, `WorkStep`, `WorkActivity`) use
`@dataclass(frozen=True)` consistent with S15/S16 Investigation models.
State transitions produce new instances via `dataclasses.replace()`.

### 2. JSON Blob Persistence
Following the `SQLiteInvestigationRepository` pattern, complex nested
objects (plan, steps, activity_log) are serialized as a JSON blob in a
single `data` column. This avoids schema migrations for plan structure
changes while keeping top-level query fields as proper columns.

### 3. Capability Invocation via Orchestrator
`WorkService._invoke_capability()` routes through the existing
`Orchestrator.route_request()` using standard `Request`/`Response`
contracts. No direct imports of Research/Memory/Cognition internals.
When no orchestrator is configured, a dry-run mock response is returned.

### 4. Bounded Execution
`run_bounded(work_id, max_steps=N)` executes at most N steps, stopping
at any terminal state (COMPLETED, FAILED, CANCELLED, PAUSED, BLOCKED,
WAITING_FOR_INPUT). No `while True` loops.

### 5. Deterministic-First Planning
`DeterministicPlanner` uses keyword matching to select from templates
(research, comparison, analysis, generic). `AIPlanner` wraps
`AIGateway` with strict JSON validation and automatic fallback to the
deterministic planner on any failure.

### 6. Step Dependencies
Steps declare `dependencies: tuple[str, ...]` referencing other step
IDs. `WorkPlan.ready_steps()` returns only steps whose dependencies
are all COMPLETED. This enables both sequential and parallel DAGs.

### 7. Failure as First-Class Result
Failed steps record `error` and `status=FAILED`. The work remains
fully inspectable. Retries are explicit via `retry_step()` with a
configurable `max_retries` per step. No silent infinite retries.

### 8. Activity Logging
Every meaningful state transition records a `WorkActivity` entry with
timestamp, type, description, and optional step_id. This provides the
structured observability that S18 (control) and S19 (presence) will
consume.

## Backward Compatibility

- No existing files were modified except `core/contracts/__init__.py`
  (additive re-exports only).
- No changes to Context, Memory, Research, Investigation, Voice, AI
  routing, or Orchestrator behavior.
- All 405 existing tests continue to pass.

## Integration Points for Future Sprints

| Future Sprint | Integration Point |
|---|---|
| S18 (Control) | `WorkStatus.PAUSED`, `pause_work()`, `cancel_work()`, step checkpoints |
| S19 (Presence) | `WorkActivity` log, `Work.status`, `Work.current_step_id` |
| S20 (Security) | `WorkStep.capability` + `input_payload` for authorization checks |
| S21 (Multi-device) | `Work` full state reconstruction via `WorkRepository.get()` |
