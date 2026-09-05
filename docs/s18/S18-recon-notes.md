# S18 Recon Notes — Human-in-the-Loop & Active Work Control

Baseline: `v1.7` @ `2961b94`
Branch:   `sprint/s18-human-control`

This document answers the 32 recon questions from S18 §28 against the
**real** S17 code, before any implementation begins.

---

## 1. Current control behavior

### Q1. What exactly does `pause_work()` currently do?
`WorkService.pause_work(work_id)` calls `_transition(work, WorkStatus.PAUSED, "Paused by user")`.
That writes:

- `Work.status = PAUSED`
- one `WorkActivity` of type `STATUS_CHANGED`, description `"paused: Paused by user"`
- `updated_at` refreshed
- `repo.update(work)` persists it

It does **not**:

- record a dedicated `WORK_PAUSED` activity
- reject re-pausing an already-paused work
- reject pausing a terminal work (`COMPLETED` / `FAILED` / `CANCELLED`)

### Q2. Why can `execute_next_step()` currently advance paused work?
Reading `service.py`:

```python
if work.status not in (WorkStatus.READY, WorkStatus.RUNNING):
    raise ValueError(...)
```
So a direct call to execute_next_step on a paused work correctly raises.
The real S17 gap is in run_bounded():

```python
while steps_executed < max_steps:
    work = self._require(work_id)
    if work.status in (COMPLETED, FAILED, CANCELLED, PAUSED, WAITING_FOR_INPUT, BLOCKED):
        break
    ...
    work = self.execute_next_step(work_id)
```
The status check is at the top of the loop. But there is no separate
mid-flight pause check inside _execute_step: once a step has entered
RUNNING, the loop will always finish that step and evaluate it, even
if a pause request arrives during the capability call. There is also no
persisted "pause requested" flag distinct from the status itself, so an
in-flight capability cannot see it.

The charter explicitly names this as the first bug S18 must fix.

Q3. What does cancel_work() currently guarantee?
Same shape as pause: transitions to CANCELLED, writes a STATUS_CHANGED
activity, persists. run_bounded respects CANCELLED at its top-of-loop
check. execute_next_step raises ValueError because CANCELLED is not
in (READY, RUNNING). But:

there is no explicit rule preventing set_status(cancelled -> running)
there is no explicit rule preventing provide_input on a cancelled work
(it would raise, but only because status ≠ WAITING_FOR_INPUT, which is
incidental, not intentional)
no dedicated WORK_CANCELLED activity type
Q4. What does provide_input() currently do?
Requires status == WAITING_FOR_INPUT, records INPUT_PROVIDED, sets status
to RUNNING, persists. It does not:

attach the input to a specific step
update any step's status (no step is ever set to WAITING_FOR_INPUT by
S17 today — the state exists in the enum but is not produced anywhere)
store the payload in metadata or step result
Q5. What states already exist?
WorkStatus: PENDING, PLANNING, READY, RUNNING, PAUSED, COMPLETED, FAILED, BLOCKED, WAITING_FOR_INPUT, CANCELLED.
StepStatus: PENDING, READY, RUNNING, COMPLETED, FAILED, SKIPPED, WAITING_FOR_INPUT.

Q6. Which states are terminal?
WorkStatus: COMPLETED, FAILED, CANCELLED.
BLOCKED is effectively terminal today because there is no unblocking
API other than manual retry_step + set_status.
StepStatus: COMPLETED, SKIPPED. FAILED is only conditionally
terminal — retry_step can revive it.

Q7. Which states are resumable?
PAUSED and WAITING_FOR_INPUT are semantically resumable, but S17 has
no resume_work() — resumption today requires the caller to know to
invoke set_status(RUNNING) or provide_input(...).

2. In-flight execution
Q8. Can a capability currently be interrupted?
No. Orchestrator.route_request is synchronous. There is no cooperative
cancellation token, no timeout, no thread/task supervision. Once
capability.invoke(request) is called, S18 cannot preempt it.

Q9. What happens if interruption arrives during execution?
It cannot arrive inside the capability. It can only be observed at safe
boundaries in _execute_step and run_bounded. Any human "stop" that
arrives while a capability is running will only take effect at the next
boundary. This is a hard constraint we must represent honestly (§9 of
the charter: do not fake cancellation).

Q10. Can execution checkpoints safely support pause?
Yes. Natural safe boundaries in _execute_step:

Before marking step RUNNING.
After capability returns, before evaluation persists.
After the final _repo.update(work) at end of step.
And in run_bounded, at the top of each loop iteration.

Q11. What state must be persisted before/after an intervention?
Requested control actions must be persistable so a subsequent
process invocation can still see them. S17 has no such field today.
After each step boundary, current Work state (status, plan, activity)
is already persisted by _repo.update.
S18 will add a small control block (persisted in the existing data JSON
blob — no schema migration needed) carrying a pending intervention flag
and reason.

3. Plan revision
Q12. How is WorkPlan currently represented?
Frozen dataclass: plan_id, steps: tuple[WorkStep, ...], version: int, created_at, updated_at, metadata.

Q13. How can a revised plan preserve previous history?
Two options:

A. Snapshot the old WorkPlan into Work.metadata["plan_history"] as a
list of serialized prior versions before replacing Work.plan.
B. Store only the diff in the activity log.

Recommendation: A — full snapshot is small, matches the "traceable
evolution" principle, and gives S19 something concrete to render.

Q14. Does plan versioning need to be explicit?
Yes. Every revision bumps WorkPlan.version and refreshes updated_at.

Q15. How can completed steps remain immutable?
Enforce in revise_plan: any step whose status ∈ {COMPLETED, SKIPPED, RUNNING} must appear unchanged and in the same relative order in the
new plan. Failure raises PlanRevisionError.

Q16. How should removed/replaced pending steps be represented?
The new plan simply omits removed steps and includes replacements as new
WorkStep entries with fresh step_ids. The old plan snapshot in
metadata["plan_history"] preserves the removed steps for inspection.

4. Approval
Q17. Where is the cleanest interception point before capability invocation?
Inside WorkService._execute_step, immediately after selecting the step
but before calling _invoke_capability(step). If the step requires
approval and no approval decision is recorded, we transition to
WAITING_FOR_APPROVAL and return.

Q18. Can approval be represented using existing Work states?
WAITING_FOR_INPUT could technically carry approval, but it conflates
two distinct semantics: "NAV asked a factual question" vs "NAV asked
permission to act." The charter (§15) allows adding a new state if the
condition is semantically distinct and requires durable state. Approval
qualifies.

Q19. Does approval require a new state?
Yes. Add:

WorkStatus.WAITING_FOR_APPROVAL = "waiting_for_approval"
StepStatus.WAITING_FOR_APPROVAL = "waiting_for_approval"
Q20. How is approval persisted?
Each pending approval is represented on the step:

StepStatus.WAITING_FOR_APPROVAL
step.metadata["approval"] = {"required": True, "requested_at": ..., "reason": ...}
Decisions are recorded as activities (APPROVAL_GRANTED / APPROVAL_REJECTED)
plus a mutation of step.metadata["approval"]["decision"].

Whether a step requires approval is determined by
step.metadata.get("requires_approval") is True. This is opt-in per step —
S20 will later attach a policy engine to decide which steps need it.

Q21. What happens if the user rejects?
Step → StepStatus.FAILED with error = "Rejected by user: <reason>".
Work → PAUSED (so the human can revise the plan or cancel).
Activity: APPROVAL_REJECTED. This is not a capability failure and is
distinguishable via step.metadata["approval"]["decision"] == "rejected".

Q22. What happens if the user modifies the requested action?
approve_step(work_id, step_id, modified_payload=...) replaces
step.input_payload, records the modification in metadata, transitions
the step to READY and the work back to RUNNING. This is essentially
a scoped one-step plan revision and also logs PLAN_REVISED.

5. Takeover
Q23. What is the smallest representation of human takeover?
Set Work.status = PAUSED and add a HUMAN_TAKEOVER activity with
metadata {"active": True}. Returning control adds CONTROL_RETURNED
{"active": False}. No new WorkStatus.

Q24. Does takeover need a new WorkStatus or an intervention record?
Intervention record is sufficient. Reusing PAUSED avoids state
explosion and satisfies §19 ("do not create a status if an intervention
record will do").

6. Activity
Q25. Which new activity types are necessary?
WORK_PAUSED
WORK_RESUMED
WORK_CANCELLED
WORK_REDIRECTED
PLAN_REVISED
INTERVENTION_REQUESTED
APPROVAL_REQUESTED
APPROVAL_GRANTED
APPROVAL_REJECTED
HUMAN_TAKEOVER
CONTROL_RETURNED
Existing INPUT_REQUESTED / INPUT_PROVIDED are reused.

Q26. Can existing WorkActivity support them?
Yes — WorkActivity already carries timestamp, activity_type, description, step_id, metadata. No structural change needed.

Q27. What information will S19 need later?
current Work.status + current_step_id
a list of pending interventions (from step metadata)
most recent 1–2 activity entries with description
for approvals: the proposed capability + payload
plan version and pending steps
All expressible from the fields above.

7. Architecture
Q28. Can S18 be implemented additively?
Yes. Additive changes:

3 new enum values in WorkStatus / StepStatus
~11 new enum values in WorkActivityType
new methods on WorkService
new actions on WorkCapability
extended JSON blob in SQLiteWorkRepository (no schema change — the
blob is opaque)
Zero existing behavior removed. _transition semantics preserved.

Q29. Is the existing WorkService boundary sufficient?
Yes. All control operations naturally belong to the same aggregate
(Work) as execution. Splitting them into a WorkController would
create split-brain state.

Q30. Is Orchestrator interception sufficient?
No interception at the Orchestrator level is required for S18. The
approval gate sits inside _execute_step before _invoke_capability.
This keeps the Orchestrator dumb and lets S20 attach authorization
independently.

Q31. Is a new controller/service actually required?
No. Extend WorkService.

Q32. Is a new ADR necessary?
Yes — one small ADR covering:

addition of WAITING_FOR_APPROVAL state
the "pending control action" persisted flag pattern
the plan-history snapshot convention
Will live at docs/architecture/decisions/0006-s18-human-control.md.

### Explicit state machine (target for S18)
```text

              PENDING
                 |
             auto_plan / set_plan
                 |
                 v
              READY  <---------------------------.
                 |                                |
       execute_next_step / run_bounded            |
                 |                                |
                 v                                |
              RUNNING --.                         |
                 |      |                         |
    +------------+------+----------+------+       |
    |            |                 |      |       |
    v            v                 v      v       |
 COMPLETED    PAUSED       WAITING_FOR_*  BLOCKED |
                 |                 |              |
             resume_work        approve/          |
                 |             provide_input      |
                 '------------------'-------------'
                 |
             cancel_work
                 |
                 v
             CANCELLED (terminal)
```
Terminal set: `{COMPLETED, FAILED, CANCELLED}`.
`BLOCKED` is recoverable via `retry_step` or `revise_plan`.

### Recon conclusion
S18 can be implemented additively on top of v1.7. No S17 contract
is broken. The primary risk area is Phase 2 (pause enforcement) — every
subsequent phase depends on the invariant that a PAUSED work never
advances, so its tests must be written first and kept green.
