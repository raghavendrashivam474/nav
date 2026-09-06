# S22 — Architectural Change Notes

## Gap 1: Missing current_step_id in Work Status Response

### 1. Observe
Scenario E1 (Approval gate) failed:
WorkCapability error: Step step_1 not found in work work_...
InteractionLayer attempted to approve step "step_1" but the actual step was named "step_deploy".

### 2. Reproduce
Deterministic test: TestScenarioEApprovalAndDenial::test_approval_required_step_pauses_for_human
Created a work with step_id "step_deploy", set requires_approval, executed, then approved via InteractionLayer. Approval failed because InteractionLayer resolved the wrong step_id.

### 3. Diagnose
- Type: A (Missing integration contract data)
- Root cause: WorkCapability._handle_status() did not include current_step_id in its response data dict. InteractionLayer reads status_resp.data.get("current_step_id") or "step_1". The fallback "step_1" is incorrect for any work whose active step has a different ID.

### 4. Evaluate
- Problem: Cross-subsystem contract gap between S17 Work and S19 Interaction
- Evidence: Scenario E1 failure, log output showing step_1 lookup
- Current architecture: WorkCapability returns status dict; InteractionLayer consumes it
- Limitation: Status dict was defined in S17 before S19 existed
- Options:
  1. Add current_step_id to status response (additive, non-breaking)
  2. Change InteractionLayer to query Work directly (breaks abstraction)
  3. Add a separate endpoint for step resolution (over-engineering)
- Recommendation: Option 1
- Compatibility: Fully backward-compatible (new key in dict)
- Migration: None required
- Testing: Scenario E1 validates the fix; S19 regression updated
- Future consequences: None — this is the correct contract shape

### 5. ADR
See: docs/architecture/decisions/0011-s22-status-current-step-id.md

### 6. Implement
Added one line to capabilities/work/capability.py:
"current_step_id": work.current_step_id,

## Deferred Findings (Type E — Future)

| ID | Finding | Reason for Deferral |
|----|---------|---------------------|
| E1 | NavContext not propagated through Orchestrator | No v1 scenario requires it |
| E2 | S21 Environment not wired into Orchestrator | Identity contracts exist; sync not needed for v1 |
| E3 | No cross-device synchronization | Explicitly out of v1 scope |
| E4 | Work redirect blocked on terminal (FAILED) state | By design — S18 policy prevents redirecting completed/failed work |
| E5 | Step retry behavior (1 retry default) | S17 design decision; not a gap |
