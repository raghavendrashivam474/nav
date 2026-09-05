---

# NAV S18 — Post-Sprint Engineering Report

**To:** Senior Development Lead
**From:** S18 Implementation Team
**Date:** 2026-09-06
**Sprint:** S18 — Human-in-the-Loop & Active Work Control
**Release:** `v1.8`
**Baseline:** `v1.7` (`2961b94`)
**Branch:** `sprint/s18-human-control`

---

## 1. Executive Summary

S18 successfully implements a comprehensive **Human Control Layer** around NAV's agentic Work subsystem. The sprint's governing principle — *"NAV may perform multi-step work within its granted authority, but the human must remain able to understand, interrupt, redirect, pause, stop, approve, reject, or take over that work"* — is now enforced at the domain and persistence level.

All 40 new tests pass. The full regression suite (498 tests) passes with zero failures. Ruff and Mypy are clean across 138 source files. No S17 contract was broken.

---

## 2. Problem Statement

S17 (`v1.7`) delivered NAV's first genuine goal-directed work loop: objective → plan → execute → evaluate → complete. However, the S17 report explicitly identified a critical gap:

> `execute_next_step()` can still advance work even when it has been marked `PAUSED`.

Beyond that specific bug, S17 had no mechanism for:

- Resuming paused work through a dedicated API
- Preventing cancelled work from being silently restarted
- Human redirection of active plans
- Approval gates before sensitive capability invocations
- Structured takeover/return-of-control semantics
- Traceable intervention history

S18 resolves all of these.

---

## 3. Architecture Overview

S18 is **additive** on top of S17. No existing contract, interface, or schema was modified in a breaking way.

```
                     NAV WORK
                        │
                   WorkService
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
     Execution     Intervention    Approval
          │             │             │
          ↓             ↓             ↓
    Orchestrator    Control flags   Step metadata
          │             │             │
          └─────────────┼─────────────┘
                        ↓
                  WorkRepository
                        ↓
                   WorkActivity
```

### What Changed

| Layer | Change | Impact |
|-------|--------|--------|
| `core/contracts/work.py` | +2 enum members (`WAITING_FOR_APPROVAL`), +11 activity types | Additive; no existing values changed |
| `capabilities/work/service.py` | +`WorkControlError`, +`PlanRevisionError`, +`_check_executable()`, +8 new methods | Additive; existing methods gained guard clauses |
| `capabilities/work/capability.py` | +8 new dispatch actions | Additive; existing actions unchanged |
| `capabilities/work/sqlite_repo.py` | None | Zero changes; new state persisted inside existing JSON blob |
| SQLite schema | None | No migration required |

### What Did NOT Change

- No new service or controller class
- No change to `Orchestrator`
- No change to `Capability` protocol
- No change to `WorkRepository` interface
- Frozen-dataclass model preserved (replace-not-mutate)
- Bounded-execution guarantee preserved
- No external agent framework introduced
- No frontend, no security plane, no vector DB

---

## 4. Detailed Implementation

### 4.1 Pause Enforcement (Phase 2) — Highest Priority

**Problem:** S17's `pause_work()` set the status to `PAUSED` but `execute_next_step()` only checked for `(READY, RUNNING)`, meaning a manual `set_status(RUNNING)` could bypass the pause. `run_bounded()` checked status at the top of its loop but not after auto-planning.

**Solution:**

- Introduced `_check_executable(work)` — a centralized guard that raises `WorkControlError` for terminal, paused, and waiting states.
- `execute_next_step()` now calls `_check_executable()` before any plan inspection.
- `run_bounded()` re-checks status after `auto_plan()` and after each step execution.
- `pause_work()` rejects terminal states and is idempotent on already-paused work.
- Emits dedicated `WORK_PAUSED` activity (in addition to `STATUS_CHANGED` for back-compat).

**Tests:** 8 tests covering pause from READY/RUNNING, idempotency, terminal rejection, bounded-loop blocking, and activity emission.

### 4.2 Resume & Cancel Semantics (Phase 3)

**`resume_work(work_id)`:**
- Only valid from `PAUSED` state; raises `WorkControlError` otherwise.
- Clears the `metadata["control"]["pending"]` intervention flag.
- Targets `RUNNING` if ready steps exist, `READY` otherwise.
- Emits `WORK_RESUMED`.

**`cancel_work(work_id)`:**
- Rejects `COMPLETED` and `FAILED` work (cannot cancel finished work).
- Idempotent on already-cancelled work.
- Emits `WORK_CANCELLED`.
- Cancelled work cannot be executed, resumed, or receive input.

**Tests:** 13 tests covering resume, cancel, cross-state rejection, and bounded-loop no-op on cancelled work.

### 4.3 In-Flight Intervention (Phase 4)

**Key constraint:** Capability execution is synchronous via `Orchestrator.route_request()`. There is no cooperative cancellation token, timeout, or thread supervision. Once `capability.invoke(request)` is called, it cannot be preempted.

**Solution:** Honest boundary model.

- `request_intervention(work_id, reason)` sets a persistent flag in `Work.metadata["control"]["pending"]`.
- `execute_next_step()` checks this flag immediately before selecting the next step. If pending, it transitions to `PAUSED` and returns.
- No false "stopped" claims — if a capability is mid-execution, the intervention takes effect at the next safe boundary.
- `resume_work()` clears the flag.

**Tests:** 5 tests covering intervention blocking, terminal rejection, activity emission, resume-clearing, and persistence across repository reloads.

### 4.4 Plan Revision & Redirect (Phase 5)

**`revise_plan(work_id, new_steps, reason)`:**

- **Immutability invariant:** Completed, running, and skipped steps must appear unchanged and in the same relative order at the front of the new step list. Any violation raises `PlanRevisionError`.
- Snapshots the current plan into `Work.metadata["plan_history"]` as a full serialized dict (using the existing `_plan_to_dict` helper).
- Increments `WorkPlan.version`.
- Emits `PLAN_REVISED`.

**`redirect_work(work_id, new_objective, new_steps, reason)`:**

- Preserves `work_id` (Work identity survives redirection).
- Optionally updates `Work.objective`.
- Delegates to `revise_plan()` if new steps are provided.
- Emits `WORK_REDIRECTED`.

**Tests:** 8 tests covering safe revision, immutability enforcement, history recording, terminal rejection, objective-only redirect, combined redirect, identity preservation, and activity emission.

### 4.5 Approval Workflow (Phase 6)

**Gate mechanism:**

- Steps opt in via `step.metadata["requires_approval"] = True`.
- `_execute_step()` checks this flag before calling `_invoke_capability()`. If approval is required and no decision is recorded, the step transitions to `StepStatus.WAITING_FOR_APPROVAL`, the work transitions to `WorkStatus.WAITING_FOR_APPROVAL`, and an `APPROVAL_REQUESTED` activity is logged.
- Execution yields control to the human.

**`approve_step(work_id, step_id, modified_payload=None)`:**
- Records `approval_decision = "approved"` in step metadata.
- If `modified_payload` is provided, replaces `step.input_payload` and logs `PLAN_REVISED` (the human changed the parameters).
- Transitions step to `READY`, work to `RUNNING`.
- Emits `APPROVAL_GRANTED`.

**`reject_step(work_id, step_id, reason)`:**
- Records `approval_decision = "rejected"` with reason and timestamp.
- Transitions step to `FAILED` with error `"Rejected by human: <reason>"`.
- Transitions work to `PAUSED` (so the human can revise the plan or cancel).
- Emits `APPROVAL_REJECTED`.
- **Important:** Rejection is semantically distinct from capability failure. The `approval_decision` metadata field makes this auditable.

**S20 boundary:** The approval gate is a pure hook driven by step metadata. S20 will later attach the policy engine that decides *which* steps get flagged and enforces authorization independently of the human decision.

**Tests:** 4 tests covering gate interception, approve-and-execute, payload modification, and reject-and-pause.

### 4.6 Input & Takeover (Phase 7)

**`request_input(work_id, step_id, prompt)`:**
- Sets step to `StepStatus.WAITING_FOR_INPUT`, work to `WorkStatus.WAITING_FOR_INPUT`.
- Emits `INPUT_REQUESTED`.

**`provide_input(work_id, input_data, step_id=None)`:**
- Enhanced from S17: now accepts an optional `step_id` and merges `input_data` into the waiting step's `input_payload`.
- Transitions step to `READY`, work to `RUNNING`.
- Emits `INPUT_PROVIDED`.

**`take_over(work_id, reason)`:**
- Pauses work (`WorkStatus.PAUSED`).
- Emits `HUMAN_TAKEOVER`.
- No new `WorkStatus` — the intervention record is sufficient (per charter §19).

**`return_control(work_id, reason)`:**
- Resumes work to `RUNNING` or `READY`.
- Emits `CONTROL_RETURNED`.

**Tests:** 2 tests covering request/provide input cycle and takeover/return cycle.

### 4.7 Capability Dispatch (Phase 8)

`WorkCapability.invoke()` now supports 17 actions:

| Action | Handler |
|--------|---------|
| `create` | `_handle_create` |
| `plan` | `_handle_plan` |
| `execute_step` | `_handle_execute_step` |
| `run_bounded` | `_handle_run_bounded` |
| `status` | `_handle_status` |
| `pause` | `_handle_pause` |
| `cancel` | `_handle_cancel` |
| `resume` | `_handle_resume` *(S18)* |
| `request_intervention` | `_handle_request_intervention` *(S18)* |
| `revise_plan` | `_handle_revise_plan` *(S18)* |
| `redirect` | `_handle_redirect` *(S18)* |
| `approve` | `_handle_approve` *(S18)* |
| `reject` | `_handle_reject` *(S18)* |
| `request_input` | `_handle_request_input` *(S18)* |
| `provide_input` | `_handle_provide_input` *(S18)* |
| `take_over` | `_handle_take_over` *(S18)* |
| `return_control` | `_handle_return_control` *(S18)* |

---

## 5. State Machine

```
              PENDING
                 │
            auto_plan / set_plan
                 │
                 ▼
              READY  ◄───────────────────────┐
                 │                            │
       execute_next_step / run_bounded         │
                 │                            │
                 ▼                            │
              RUNNING ──┐                      │
                 │      │                      │
    ┌────────────┼──────┼──────────┐           │
    │            │      │          │           │
    ▼            ▼      ▼          ▼           │
 COMPLETED    PAUSED  WAITING   BLOCKED        │
                 │    FOR_*                    │
             resume /   │                      │
            return_ctrl │                      │
                 │      │                      │
                 └──────┴──────────────────────┘
                 │
             cancel_work
                 │
                 ▼
             CANCELLED (terminal)
```

**Terminal set:** `{COMPLETED, FAILED, CANCELLED}`
**Resumable:** `PAUSED`, `WAITING_FOR_INPUT`, `WAITING_FOR_APPROVAL`, `BLOCKED`

---

## 6. Quality Metrics

| Metric | Result |
|--------|--------|
| New S18 tests | 40 (all passing) |
| Full regression suite | 498 passed, 1 skipped, 2 deselected |
| Ruff | All checks passed |
| Mypy | 0 errors in 138 source files |
| Pre-existing mypy errors fixed | 2 (union-attr in `test_s17_work.py`) |
| S17 regressions | 0 |
| SQLite schema migrations | 0 |
| New dependencies | 0 |

---

## 7. Documentation Deliverables

| File | Status |
|------|--------|
| `docs/s18/S18-recon-notes.md` | ✅ Complete (32 recon questions answered) |
| `docs/s18/baseline.md` | ✅ Complete |
| `docs/s18/S18-plan.md` | ✅ Complete |
| `docs/s18/implementation.md` | ✅ Complete (Phases 2–8 documented) |
| `docs/s18/architectural_change_notes.md` | ✅ Complete |
| `docs/s18/completion-report.md` | ✅ Complete (all acceptance criteria checked) |
| `docs/s18/post_completion-report.md` | ✅ This document |
| `docs/architecture/decisions/0006-s18-human-control.md` | ✅ ADR accepted |

---

## 8. Forward Integration Points

### S19 (Interaction Layer)
S18 provides the structured state that S19 will render:
- `Work.status` + `Work.current_step_id` for real-time status display
- `Work.activity_log` for the activity strip (no chain-of-thought exposed)
- Pending approvals discoverable via `step.metadata["requires_approval"]` and `step.metadata["approval_decision"]`
- All 17 capability actions available for voice/UI dispatch

### S20 (Security & Authorization)
- The approval gate is a pure hook; S20 attaches the policy that sets `requires_approval` and enforces authorization independently.
- Future execution chain: `Human approval (S18) → Security authorization (S20) → Capability execution`.
- Neither layer silently replaces the other.

### S21 (Multi-Device Synchronization)
- S18 persists enough state for future sync: `Work.status`, `metadata["control"]`, `metadata["plan_history"]`, approval decisions, intervention flags.
- S21 will solve conflict resolution, device handoff, and concurrent control.

---

## 9. Known Limitations & Deferred Items

1. **Synchronous capability execution:** Capabilities cannot be interrupted mid-call. Intervention takes effect at the next step boundary. This is an honest representation — we do not fake cancellation.

2. **No concurrent Work execution:** S17 deferred this; S18 preserves that decision. The bounded execution model is single-threaded per Work item.

3. **Approval policy is opt-in:** Steps must explicitly set `requires_approval = True` in metadata. The automated policy engine that decides which steps need approval is deferred to S20.

4. **No timeout/escalation:** If a human does not respond to an approval or input request, NAV waits indefinitely. The safe default is *"when human input is required and unavailable, NAV waits."* Timeout behavior can be added in a future sprint if needed.

---

## 10. Conclusion

S18 transforms NAV from an autonomous executor into a **human-steerable agent**. The human can now say "Go," "Pause," "Change direction," "Do this one," "Stop," "I'll take over," and "Continue" — and NAV will respond correctly at every boundary, with full traceability and zero silent substitutions.

S17 built the hands. S18 gives the human the ability to guide those hands. S19 will make that guidance feel natural.

**S18 is closed and ready for merge to `main` and tagging as `v1.8`.**

---

*End of report.*