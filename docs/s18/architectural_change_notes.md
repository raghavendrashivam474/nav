# S18 Architectural Change Notes

## Summary
S18 introduces the **Human Control Layer around Work**, keeping NAV's agentic behavior steerable, interruptible, inspectable, and bounded by human decisions without violating S17 contracts.

## Key Architectural Additions

1. **Enums & States**:
   - `WorkStatus.WAITING_FOR_APPROVAL` & `StepStatus.WAITING_FOR_APPROVAL`.
   - 11 new `WorkActivityType` entries (`WORK_PAUSED`, `WORK_RESUMED`, `WORK_CANCELLED`, `WORK_REDIRECTED`, `PLAN_REVISED`, `INTERVENTION_REQUESTED`, `APPROVAL_REQUESTED`, `APPROVAL_GRANTED`, `APPROVAL_REJECTED`, `HUMAN_TAKEOVER`, `CONTROL_RETURNED`).

2. **Pause Enforcement & Safe Boundaries**:
   - Added `_check_executable()` guard in `WorkService` preventing advancement of paused/cancelled/waiting items.
   - Introduced `WorkControlError` and `PlanRevisionError`.

3. **Immutable History & Plan Snapshots**:
   - Completed/running steps in `WorkPlan` cannot be modified or reordered during revisions.
   - Plan revisions increment `WorkPlan.version` and store full snapshots in `Work.metadata["plan_history"]`.

4. **Human Approval Hooks**:
   - Step execution checks `step.metadata["requires_approval"]` before invoking the Orchestrator, pausing at `WAITING_FOR_APPROVAL`.
   - `approve_step` supports parameter modification on the fly.

5. **Takeover & Return of Control**:
   - Supports pausing execution with a `HUMAN_TAKEOVER` activity and resuming with `CONTROL_RETURNED`.

See `docs/architecture/decisions/0006-s18-human-control.md` for full ADR details.
