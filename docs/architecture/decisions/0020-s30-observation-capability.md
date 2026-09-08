# ADR-0020: S30 Observation Capability

## Status

Accepted

## Context

S29 (Action) gave NAV the ability to perform controlled external
operations. However, S29 ends at `ActionResult` — the immediate
execution status. There is no mechanism to distinguish between
"the action execution returned success" and "the expected external
state actually changed."

An action may report `SUCCEEDED` while the external state did not
change (e.g., idempotent no-op). Conversely, an action may report
`UNKNOWN` (e.g., network interruption) while the external system
actually processed the request.

NAV needs an explicit, inspectable primitive for representing what
it can establish about external state after interaction.

## Decision

Introduce a first-class Observation capability (S30) that:

1. Provides structured `Observation`, `ObservationRequest`, and
   `ObservationResult` contracts.
2. Distinguishes observation state (`OBSERVED`, `NOT_OBSERVED`,
   `CONFLICTING`, `UNKNOWN`, `INVALID`) from action execution state.
3. Uses bounded, explicit observation adapters (no unrestricted
   scanning or probing).
4. Preserves honest uncertainty — unknown observations remain unknown.
5. Supports optional linkage to S29 actions via `action_id`.
6. Treats all external content as untrusted data.
7. Does NOT trigger actions, persist data, or integrate with Memory.

## Consequences

### Positive
- NAV can now explicitly represent post-action external state.
- Foundation for future Memory and adaptive Reasoning.
- Clear separation between execution status and observed consequence.
- Honest uncertainty prevents false confidence.

### Negative
- New subsystem adds surface area.
- Bounded adapters limit immediate utility (by design).
- No persistence means observations are invocation-scoped.

### Neutral
- `ReasoningInputType.OBSERVATION` already existed in S27; S30
  provides the first producer for that input type.

## Alternatives Considered

1. **Extend ActionResult with observation fields**: Rejected.
   Observation and execution are fundamentally different concerns.
   Coupling them would violate single-responsibility and make the
   Action contract unstable.

2. **Build observation into Memory directly**: Rejected. Memory
   (S6/S13) is key-value persistence. Observation is an epistemological
   primitive. Conflating them would prevent future independent
   evolution.

3. **Use S23 SourceMetadata for provenance**: Rejected. SourceMetadata
   is acquisition-specific (URLs, provider IDs). Observation provenance
   has different semantics.

## References

- S29 Action: `docs/architecture/decisions/0019-s29-action-capability.md`
- S27 Reasoning: `core/contracts/reasoning.py` (ReasoningInputType.OBSERVATION)
- S30 Recon: `docs/s30/S30-recon-notes.md`
