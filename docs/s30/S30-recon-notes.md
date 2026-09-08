# S30 Reconnaissance Notes

## Baseline Verification

- v2.6 confirmed at `9b4d801`, clean tree, `v2.6` tag present.
- 1051 tests passing (2 deselected) before any S30 work.

## S29 Action Layer (Primary Dependency)

- `ActionRequest`: frozen dataclass with `MappingProxyType` for dicts.
  Fields: `action_type`, `target`, `parameters`, `requester_id`, `source`,
  `decision_id`, `metadata`.
- `ActionResult`: frozen dataclass. Fields: `action_id`, `action_type`,
  `state`, `outcome`, `message`, `target`, `executed_at`, `metadata`.
- `ActionState`: REQUESTED → VALIDATED → AUTHORIZED → EXECUTING →
  SUCCEEDED/FAILED/UNKNOWN. Terminal: SUCCEEDED, FAILED, REJECTED,
  CANCELLED, UNKNOWN.
- `ActionOutcome`: SUCCESS, FAILURE, REJECTION, UNKNOWN.
- State-outcome consistency enforced in `__post_init__`.
- Engine uses `AuthorizerFn` callable + `ExecutionAdapter` callable.
- Two adapters: ECHO (returns params), LOG (structured log entry).
- Default authorizer is fail-closed (SYSTEM_ACTOR only).

## S28 Decision Layer

- `DecisionResult` links to `evidence_basis` tuple.
- `DecisionState`: DECIDED, CONTESTED, INCONCLUSIVE, INSUFFICIENT_INPUTS,
  NO_FEASIBLE_ALTERNATIVE.
- No modification needed. Observation may eventually feed back into
  decision context, but not in S30.

## S27 Reasoning Layer

- `ReasoningInputType` already includes `OBSERVATION = "observation"`.
  S30 fits naturally into the existing reasoning input taxonomy.
- No modification needed.

## S24 Evidence / Provenance

- `SourceMetadata` (S23) is acquisition-specific: `source_name`,
  `source_url`, `provider_id`, `retrieved_at`, `query_echo`.
- Not suitable for observation provenance (different semantics).
- S30 introduces its own lightweight `provenance` string field on
  `Observation`, plus `ObservationSource` enum.

## S23 External Information

- `ExternalInformationItem` references `SourceMetadata` directly.
- No overlap with S30 observation semantics.

## Memory (S6/S13)

- `MemoryRecord`: key-value with tags. Completely different shape.
- `MemoryCapabilityInterface`: store/retrieve/update/forget.
- S30 must NOT overlap with Memory. Observation is a snapshot;
  Memory is persistence. Future integration point, not S30 scope.

## Security (Sx1)

- `ActorIdentity`: `actor_id`, `actor_type`, `trust_level`.
- `AuthorizationRequest/Decision/Outcome`: existing authorization flow.
- `SYSTEM_ACTOR`: default trusted identity.
- S30 observations do not require authorization (they are reads, not
  writes). However, the capability layer preserves Sx1 patterns for
  future extensibility.

## Capability Contract

- `Request`: `request_id`, `payload` (dict). No `capability` field.
- `Response`: `request_id`, `data`, `success`, `error`.
- `Capability` ABC: `name`, `version`, `description`, `invoke()`.

## Architectural Gaps Identified

1. No observation primitive exists. S29 ends at `ActionResult`.
2. No mechanism to distinguish execution status from observed state.
3. No structured representation of post-action external state.
4. `ReasoningInputType.OBSERVATION` exists but has no producer.

## Proposed S30 Boundary

- New subsystem: `capabilities/observation/`
- New contract: `core/contracts/observation.py`
- Three contracts: `ObservationRequest`, `Observation`, `ObservationResult`
- Two enums: `ObservationSource`, `ObservationState`
- Engine with bounded adapters (ECHO, LOCAL_STATE registry)
- No persistence, no memory, no action triggering
- No modification to any frozen subsystem

## ADR

- Next ADR number: 0020
- Location: `docs/architecture/decisions/0020-s30-observation-capability.md`
