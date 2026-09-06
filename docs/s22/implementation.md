# S22 — Implementation Notes

## Production Code Changes

### 1. capabilities/work/capability.py (ADDITIVE FIX)

**File:** `capabilities/work/capability.py`
**Method:** `WorkCapability._handle_status()`
**Change:** Added `"current_step_id": work.current_step_id` to the
status response data dictionary.

**Before:**
```python
data: dict[str, Any] = {
    "work_id": work.work_id,
    "objective": work.objective,
    "status": work.status.value,
    "completed_steps": len(work.completed_steps()),
    "pending_steps": len(work.pending_steps()),
    "activity_count": len(work.activity_log),
}
```
**After:**

```Python

data: dict[str, Any] = {
    "work_id": work.work_id,
    "objective": work.objective,
    "status": work.status.value,
    "current_step_id": work.current_step_id,
    "completed_steps": len(work.completed_steps()),
    "pending_steps": len(work.pending_steps()),
    "activity_count": len(work.activity_log),
}
```

Rationale: InteractionLayer._handle_control_action() reads
current_step_id from the status response to resolve which step to
approve/reject/provide-input on. Without this field, the layer fell
back to "step_1", breaking approval for any step with a different ID.
This was a genuine cross-subsystem integration gap between S17 (Work)
and S19 (Interaction).

Impact: Purely additive. No existing caller is affected because
the new key is simply present in the response dict. Existing tests
that check for specific keys were updated (see below).

2. **demo_s19.py (MYPY FIX)**
   - **File:** `demo_s19.py`
   - **Line:** 37
   - **Change:** Added `# type: ignore[import-not-found]` to the `from ai.router import ModelRouter` import.
   - **Rationale:** Pre-existing mypy error. The `ai.router` module is an optional runtime dependency not available during static analysis.

### Test Code Changes

3. **tests/test_s22_scenarios.py (NEW — 22 tests)**
   - Complete end-to-end integration test suite covering 8 scenarios (A-H) with 22 individual test cases. Validates the full NAV v1 architecture across Interaction, Orchestrator, Security, Work, Human Control, Voice, and Environment subsystems.

4. **tests/test_s19_status_activity.py (REGRESSION UPDATE)**
   - **File:** `tests/test_s19_status_activity.py`
   - **Test:** `test_legacy_status_payload_unchanged`
   - **Change:** Added `"current_step_id"` to `expected_keys` set.
   - **Rationale:** Per S22 Regression Rule (Brief §17): the S22 fix intentionally changed the status response shape. The old assertion was obsolete because `current_step_id` is now a required integration contract between WorkCapability and InteractionLayer.

### What Was NOT Changed

- **S17 Work contracts** — untouched
- **S18 Human Control** — untouched
- **S19 Interaction boundary** — untouched
- **S19 Presence model** — untouched
- **S19 Voice adapter** — untouched
- **S20 Security plane** — untouched
- **S21 Environment identity** — untouched
- **Orchestrator dispatch logic** — untouched
- **WorkService lifecycle** — untouched