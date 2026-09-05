# ADR 0006: Human-in-the-Loop & Active Work Control Subsystem

- **Status:** Accepted
- **Date:** S18 Release
- **Context:** S17 introduced goal-directed Work loops (objective -> plan -> step execution -> evaluation -> complete). S18 enables genuine human control and agency over active work: pausing, resuming, cancelling, in-flight intervention flags, plan revision, human redirection, approval gates, input requests, and manual takeover.

## Decision

1. **State Machine Additions**:
   - `WorkStatus.WAITING_FOR_APPROVAL`: Distinguishes approval gates from general user queries (`WAITING_FOR_INPUT`).
   - `StepStatus.WAITING_FOR_APPROVAL`: Marks individual steps awaiting human authorization.
   - 11 new `WorkActivityType` entries to provide transparent auditability of human interventions.

2. **Pause & Resume Enforcements**:
   - `execute_next_step` strictly checks `_check_executable` and refuses to run paused, waiting, cancelled, or terminal work items.
   - `run_bounded` checks work state before and after each step boundary.
   - `resume_work` explicitly clears pending intervention flags and resumes execution to `RUNNING` or `READY`.

3. **In-Flight Intervention Checkpoints**:
   - Synchronous capability execution cannot be forcibly preempted mid-call.
   - A persistent intervention flag in `metadata["control"]["pending"]` is checked at safe execution boundaries immediately before capability invocation.

4. **Plan Revision & History Invariants**:
   - Completed, running, and skipped steps are strictly immutable. Any attempt to mutate, reorder, or delete them raises `PlanRevisionError`.
   - Prior plan versions are snapshot into `metadata["plan_history"]` when `revise_plan` is invoked, and `WorkPlan.version` is incremented.
   - `redirect_work` preserves Work identity while allowing objective and step revision.

5. **Approval Workflow Hook**:
   - Steps requiring approval set `metadata["requires_approval"] = True`.
   - `_execute_step` pauses execution at `WAITING_FOR_APPROVAL` until `approve_step` (with optional parameter modification) or `reject_step` is called.

## Consequences

- Retains 100% backwards compatibility with S17 contracts.
- Provides clean, well-defined integration hooks for S19 (visual/voice interaction) and S20 (security authorization engine).
