# S22 — Reconnaissance Notes

## Orchestrator Integration Points

| Integration | Status | References |
|-------------|--------|------------|
| Security | ✅ WIRED | 18 references — S20 enforcement at dispatch |
| Capability lookup | ✅ WIRED | 10 references — registry-based dispatch |
| Work service | ✅ WIRED | 1 reference — via WorkCapability |
| Context propagation | ❌ NOT WIRED | NavContext not passed through Orchestrator |
| Environment/device | ❌ NOT WIRED | S21 identities not in Orchestrator path |
| Human control | ✅ WIRED | 4 references — approval enrichment |
| Activity/status | ❌ NOT WIRED | No direct activity aggregation |

## Key Architectural Observations

### 1. Orchestrator is thin and security-gated
`Orchestrator.route_request()` performs S20 authorization check, then
dispatches to `CapabilityRegistry.get(target).invoke(request)`. No
context propagation, no environment awareness. Clean separation.

### 2. InteractionLayer is the integration hub
`InteractionLayer` wires together:
- `CommandInterpreter` (text → UserAction)
- `WorkControlAdapter` (UserAction → Orchestrator → WorkCapability)
- `InteractionSession` (focused_work_id, transient states)
- Presence state derivation from Work status

### 3. WorkCapability is the Work subsystem's Orchestrator interface
`WorkCapability.invoke()` maps `action` payload strings to `WorkService`
methods. Supports: create, plan, execute_step, run_bounded, status,
pause, cancel, resume, redirect, approve, reject, provide_input,
take_over, return_control.

### 4. S21 Environment is standalone
`RuntimeRegistry`, `RuntimeIdentity`, `DeviceIdentity`, `StateOrigin`
exist as contracts and in-memory registry. Not wired into Orchestrator
or WorkService. Coexists without interference.

### 5. Voice adapter is a clean wrapper
`InteractionVoiceAdapter.run_voice_cycle()` chains:
Microphone → STT → InteractionLayer.process_input() → TTS → Speaker.
Returns None on any hardware/transcription failure.

## Critical Gap Discovered

**WorkCapability._handle_status did not expose `current_step_id`.**

`InteractionLayer._handle_control_action()` queries work status to
resolve the active step for approve/reject/input actions. It reads
`status_resp.data.get("current_step_id")`. Because WorkCapability
omitted this field, the InteractionLayer fell back to `"step_1"`,
breaking approval for any step with a different ID.

**Classification:** Type A (Missing integration contract data)
**Severity:** v1-critical — breaks S18 approval through S19 interaction
**Resolution:** Added `"current_step_id": work.current_step_id` to
`WorkCapability._handle_status` response data.
