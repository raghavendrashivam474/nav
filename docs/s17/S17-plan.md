# S17 Implementation Plan — Technical Intelligence & Agentic Workflows

## Phase 1: Core Contracts & Data Models
- File: `core/contracts/work.py`
  - `WorkStatus`, `StepStatus`, `WorkActivityType`
  - `WorkStep`, `WorkPlan`, `WorkActivity`, `Work`
  - `WorkQuery`
  - Protocols: `PlannerProtocol`, `StepEvaluatorProtocol`
- File: `core/contracts/__init__.py`
  - Export new work contracts.

## Phase 2: Persistence Layer
- File: `capabilities/work/repository.py`
  - `WorkRepository` ABC (CRUD + Query).
- File: `capabilities/work/sqlite_repo.py`
  - `SQLiteWorkRepository` storing work rows and JSON serialization of plans, steps, and activity log.

## Phase 3: Planning & Evaluation Subsystem
- File: `capabilities/work/planner.py`
  - Deterministic planner (pre-defined templates & heuristic decomposition).
  - AI-assisted planner (using `AIGateway` with strict schema validation and fallback).
- File: `capabilities/work/evaluator.py`
  - Deterministic step evaluator assessing result success, dependency completion, and next-step readiness.

## Phase 4: Work Service & Execution Engine
- File: `capabilities/work/service.py`
  - Lifecycle methods: `create_work`, `set_plan`, `execute_step`, `run_bounded`, `retry_step`, `pause_work`, `cancel_work`.
  - Integration with `Orchestrator` / `CapabilityRegistry`.
  - Contextual initialization via `NavContext`.
  - Step checkpointing, failure capture, and activity logging.

## Phase 5: Work Capability Integration
- File: `capabilities/work/capability.py`
  - `WorkCapability(Capability)` wrapping `WorkService` for Orchestrator discovery.
- File: `capabilities/work/__init__.py`
  - Clean exports for the work capability package.

## Phase 6: Comprehensive Test Suite
- File: `tests/test_s17_work.py`
  - Model immutability, validation, and JSON serialization roundtrips.
  - SQLite repository CRUD, search, and activity persistence.
  - Deterministic and AI-assisted planning with schema validation and error fallback.
  - Step-by-step execution, bounded execution loops (`max_steps`), failure recording, retries.
  - Dependency resolution (parallel/sequential steps).
  - Context integration (`create_from_context`).
  - Interruption and resume recovery across fresh repository instances.
  - Full regression check across existing tests (S1-S16).

## Phase 7: Quality Verification & Documentation
- Run `pytest`, `ruff check .`, `mypy`.
- Documentation:
  - `docs/s17/implementation.md`
  - `docs/s17/architectural_change_notes.md`
  - `docs/s17/completion-report.md`
  - `docs/s17/post_completion-report.md`
- Git release tagging & merge protocol.
