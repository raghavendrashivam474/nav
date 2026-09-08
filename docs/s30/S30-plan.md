# S30 Plan

## Objective

Establish a first-class Observation primitive that allows NAV to
explicitly represent what it can establish about external state or
effects after actions or direct inspection.

## Contracts

### ObservationSource (enum)
- `DIRECT_INSPECTION` — NAV directly inspected the target.
- `ACTION_RESULT` — Derived from an S29 ActionResult.
- `EXTERNAL_REPORT` — Reported by an external system.
- `LOCAL_STATE` — Read from NAV's local runtime state.
- `UNKNOWN` — Source cannot be determined.

### ObservationState (enum)
- `OBSERVED` — State successfully established.
- `NOT_OBSERVED` — Inspected; expected state not found.
- `CONFLICTING` — Multiple observations disagree.
- `UNKNOWN` — State could not be established.
- `INVALID` — Observation data is malformed.

### ObservationRequest (frozen dataclass)
- `subject: str` — What to observe.
- `source: ObservationSource` — How to observe.
- `action_id: str | None` — Optional S29 linkage.
- `parameters: dict` — Frozen via MappingProxyType.
- `requester_id: str` — Who requested.
- `metadata: dict` — Frozen extension data.

### Observation (frozen dataclass)
- `observation_id: str`
- `source: ObservationSource`
- `subject: str`
- `observed_state: str` — What was established.
- `state: ObservationState`
- `observed_at: datetime`
- `action_id: str | None`
- `provenance: str`
- `metadata: dict` — Frozen.

### ObservationResult (frozen dataclass)
- `observation_id: str`
- `subject: str`
- `state: ObservationState`
- `observation: Observation | None`
- `message: str`
- `observed_at: datetime | None`
- `metadata: dict` — Frozen.

## Engine

- `ObservationEngine` with bounded adapter registry.
- Adapters: ECHO (testing), LOCAL_STATE (injectable registry).
- Lifecycle: validate → observe → construct result.
- No action triggering, no persistence, no learning.

## Service

- `ObservationService` facade delegating to engine.

## Capability

- `ObservationCapability` implementing `Capability` ABC.
- Single action: `observe`.
- Payload: `subject`, `source`, optional `action_id`, `parameters`.

## Testing

- Contract tests (immutability, validation, state semantics).
- Engine tests (adapters, unknown handling, determinism).
- Service tests (delegation).
- Capability tests (payload parsing, error handling).
- Adversarial tests (injection, provenance spoofing, semantic
  inflation, fake linkage, unknown honesty, escalation).

## Boundaries

- No Memory integration.
- No Reasoning feedback loop.
- No Action triggering.
- No persistence.
- No modification to S23–S29 or Sx1.
