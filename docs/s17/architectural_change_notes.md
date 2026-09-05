# S17 Architectural Change Notes

## Summary

S17 is a purely **additive** sprint. No existing architectural contracts
were modified, broken, or replaced.

## Changes Made

### 1. New Contract Module: `core/contracts/work.py`
- **Type:** Additive
- **Impact:** None on existing code
- **Details:** Introduces `Work`, `WorkPlan`, `WorkStep`, `WorkStatus`,
  `StepStatus`, `WorkActivity`, `WorkActivityType`, `WorkQuery`,
  `PlannerProtocol`, `StepEvaluatorProtocol`, `WorkCapabilityInterface`.

### 2. Updated Re-exports: `core/contracts/__init__.py`
- **Type:** Additive (new imports and `__all__` entries)
- **Impact:** None on existing consumers
- **Details:** Added S17 work contracts to the unified export surface.
  All existing exports remain unchanged.

### 3. New Capability Package: `capabilities/work/`
- **Type:** Additive
- **Impact:** None on existing capabilities
- **Details:** Self-contained work subsystem with its own repository,
  planner, evaluator, service, and capability wrapper.

## No ADR Required

The changes do not alter any existing architectural boundary, contract,
or behavioral invariant. The Work subsystem is a new capability that
composes with existing infrastructure (Orchestrator, CapabilityRegistry,
AIGateway) through established interfaces.

If future sprints (S18-S21) require modifications to the Work contracts
or execution model, an ADR should be created at that time.

## Verification

- All 405 pre-existing tests pass without modification.
- Ruff and Mypy report zero new issues.
- No new external dependencies introduced.
