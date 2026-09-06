# ADR 0011: Expose `current_step_id` in Work Status Response

**Status:** Accepted
**Sprint:** S22
**Date:** 2026-09-06

## Context

The S19 `InteractionLayer._handle_control_action()` method resolves the
active step for approve/reject/provide_input actions by reading
`current_step_id` from the Work status response. However, the S17
`WorkCapability._handle_status()` method did not include this field in
its response data dictionary.

This caused the InteractionLayer to fall back to a hardcoded `"step_1"`
default, which broke approval workflows for any work whose active step
had a different identifier.

## Decision

Add `"current_step_id": work.current_step_id` to the status response
data dictionary in `WorkCapability._handle_status()`.

## Consequences

### Positive
- Fixes cross-subsystem integration between S17 Work and S19 Interaction
- Enables correct step resolution for approve/reject/input actions
- Purely additive — no existing callers are affected
- Aligns the status response with the actual `Work` dataclass shape

### Negative
- S19 regression test `test_legacy_status_payload_unchanged` required
  updating its expected key set (documented, deliberate)

### Neutral
- The `current_step_id` field may be `None` when no step is active.
  Callers already handle this via `.get("current_step_id") or "step_1"`.
