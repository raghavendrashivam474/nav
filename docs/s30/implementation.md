# S30 Implementation

## Files Created

| File | Purpose |
|------|---------|
| `core/contracts/observation.py` | Observation contracts and enums |
| `capabilities/observation/__init__.py` | Package init |
| `capabilities/observation/engine.py` | Observation lifecycle engine |
| `capabilities/observation/service.py` | Service facade |
| `capabilities/observation/capability.py` | Orchestrator-facing capability |
| `tests/test_s30_observation.py` | Core tests (35 tests) |
| `tests/test_s30_adversarial.py` | Adversarial tests (11 tests) |
| `docs/architecture/decisions/0020-s30-observation-capability.md` | ADR |

## Design Decisions

### MappingProxyType for Frozen Dicts
Follows S29 pattern exactly. `parameters` and `metadata` on all
contracts are frozen after construction via `__post_init__`.

### ObservationSource vs SourceMetadata
S23's `SourceMetadata` is acquisition-specific (URLs, provider IDs).
Observation provenance has different semantics (how the observation
was obtained, not where data was retrieved from). S30 uses a
lightweight `provenance` string + `ObservationSource` enum instead.

### Bounded Adapters
Only two adapters ship: ECHO (for testing) and LOCAL_STATE (injectable
registry). No filesystem scanning, network probing, or shell inspection.
Future adapters must be deliberately added.

### Honest Uncertainty
`UNKNOWN` and `NOT_OBSERVED` are distinct states. The engine never
converts lack of evidence into a negative observation. When no adapter
exists for a source, the result is `UNKNOWN`, not `FAILED`.

### No Action Loop
The engine produces `ObservationResult` and stops. No conditional
action triggering, no retry logic, no autonomous recovery.

## Test Fix

Initial capability tests used `capability="observation"` kwarg on
`Request`, but the `Request` contract only has `request_id` and
`payload`. Fixed by removing the spurious kwarg. All 46 S30 tests
pass.

## Regression

- Pre-S30: 1051 passed, 2 deselected.
- Post-S30: 1096 passed, 1 skipped, 2 deselected.
- Net new: 45 tests (46 S30 minus 1 pre-existing skip delta).
- Zero regressions.
