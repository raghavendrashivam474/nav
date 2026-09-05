
S18 Sprint Plan — Human-in-the-Loop & Active Work Control
Baseline: v1.7 (2961b94)
Target: v1.8
Branch: sprint/s18-human-control

Governing principle (charter §2):

NAV may perform multi-step work within its granted authority, but the
human must remain able to understand, interrupt, redirect, pause,
stop, approve, reject, or take over that work.

### Phase 1 — Recon & baseline ✅ (this commit)
- `docs/s18/S18-recon-notes.md`
- `docs/s18/baseline.md`
- `docs/s18/S18-plan.md`

### Phase 2 — Pause enforcement (highest priority)
- Add `WorkActivityType.WORK_PAUSED` / `WORK_RESUMED` / `WORK_CANCELLED` / `INTERVENTION_REQUESTED`.
- Add persisted "pending control" flag in `Work.metadata["control"]` (JSON, no schema migration).
- `pause_work`:
  - reject on terminal states
  - idempotent when already paused
  - emit `WORK_PAUSED`
- `execute_next_step`: reject on `PAUSED` / `CANCELLED` with explicit domain exceptions.
- `run_bounded`:
  - top-of-loop status check (existing)
  - plus re-check `_require(work_id).status` immediately before calling `execute_next_step`, so a pause requested during a previous step's persistence is honored.
- Tests: `tests/test_s18_pause_enforcement.py`.

### Phase 3 — Resume & cancel semantics
- `resume_work(work_id)` → `PAUSED` → `READY|RUNNING`, emits `WORK_RESUMED`.
- `cancel_work` emits `WORK_CANCELLED` (in addition to `STATUS_CHANGED` for back-compat).
- Rejects: resume on non-`PAUSED`; approval/input on cancelled work.
- Tests: `tests/test_s18_resume_cancel.py`.

### Phase 4 — In-flight intervention semantics
- Document the honest boundary model.
- `request_intervention(work_id, kind, reason)` records `INTERVENTION_REQUESTED` and sets `Work.metadata["control"]["pending"]`.
- Enforcement at safe boundaries only. No fake cancellation.
- Tests: `tests/test_s18_intervention.py`.

### Phase 5 — Redirect & plan revision
- `revise_plan(work_id, new_steps, reason)`:
  - preserves completed/running/skipped steps in order
  - snapshots old plan into `Work.metadata["plan_history"]`
  - bumps `WorkPlan.version`
  - emits `PLAN_REVISED`
- `redirect_work(work_id, new_objective=None, new_steps=None, reason)`:
  - same Work ID
  - updates `Work.objective` if provided
  - calls `revise_plan` internally
  - emits `WORK_REDIRECTED`
- New exception: `PlanRevisionError`.
- Tests: `tests/test_s18_plan_revision.py`.

### Phase 6 — Approval workflow
- Add `WorkStatus.WAITING_FOR_APPROVAL` and `StepStatus.WAITING_FOR_APPROVAL`.
- Add `WorkActivityType.APPROVAL_REQUESTED` / `GRANTED` / `REJECTED`.
- In `_execute_step`, if `step.metadata.get("requires_approval")` is True and no decision recorded, transition step + work to `WAITING_FOR_APPROVAL` and return.
- `approve_step(work_id, step_id, modified_payload=None)`.
- `reject_step(work_id, step_id, reason)` → step `FAILED`, work `PAUSED`.
- Approval decisions survive restart (persisted in step metadata).
- Tests: `tests/test_s18_approval.py`.

### Phase 7 — Input & takeover
- `request_input(work_id, step_id, question, ...)` sets step + work to `WAITING_FOR_INPUT`, emits `INPUT_REQUESTED`.
- `provide_input(work_id, input_data, step_id=None)` attaches input to the waiting step, transitions step to `READY`, work to `RUNNING`.
- `take_over(work_id, note)` → work `PAUSED`, `HUMAN_TAKEOVER` activity.
- `return_control(work_id, note)` → resume, `CONTROL_RETURNED` activity.
- Tests: `tests/test_s18_input_takeover.py`.

### Phase 8 — Capability + observability
- Register new actions in `WorkCapability.invoke`: `resume`, `revise_plan`, `redirect`, `approve`, `reject`, `request_input`, `take_over`, `return_control`, `request_intervention`.
- Add `list_activities(work_id, limit)` convenience for future S19.
- Tests: `tests/test_s18_capability.py`.

### Phase 9 — Full verification
- `pytest -q` — all pass, no regressions.
- `ruff check .` — clean.
- `mypy .` — clean (also fixes the two pre-existing errors in `tests/test_s17_work.py`).

### Phase 10 — Documentation & release
- `docs/s18/implementation.md`
- `docs/s18/architectural_change_notes.md`
- `docs/architecture/decisions/0006-s18-human-control.md`
- `docs/s18/completion-report.md`
- `docs/s18/post_completion-report.md`
- Merge `sprint/s18-human-control` → `main`.
- Tag `v1.8` (annotated).
- Push. Verify. Delete sprint branch.

### Acceptance criteria (from charter §47)
Tracked as a live checklist in `completion-report.md`.

## Non-goals for S18
- No React UI, no voice UI, no dashboard.
- No security / authorization plane (S20).
- No agent framework (LangChain, CrewAI, AutoGen).
- No vector DB, no distributed sync (S21).
- No concurrent work execution.
- No AI-driven autonomous plan replacement.

## Invariants preserved
- Bounded execution (`max_steps`).
- Frozen dataclasses + replace-not-mutate.
- No direct capability imports from `WorkService`.
- Single persistence layer (`SQLiteWorkRepository`).
- Single activity system (`WorkActivity`).
- No hard-coded AI provider.
