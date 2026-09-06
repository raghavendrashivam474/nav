# ADR 0012: External Information Capability Architecture

## Status

**Accepted** — S23 Implementation Complete

## Sprint

S23 — External Information Capability (NAV v2)

## Context

NAV v1.12 has no first-class mechanism for acquiring external information.
Research and cognition infrastructure exists, but external retrieval is not
established as a governed capability boundary. S22 identified this gap in
the integration validation pipeline.

S23 must introduce external information acquisition without modifying the
frozen v1.12 baseline (Orchestrator, Security Plane, Context, Work,
Interaction, Environment).

## Decision

### D1: Additive capability — no architectural change (Case A)

The external information capability is added as a new module within the
existing capability dispatch pattern. No existing subsystem is modified.

**Rationale:** Reconnaissance confirmed the Orchestrator, S20 Security
Plane, and NavContext propagation already support new capabilities without
structural changes. Introducing a parallel dispatch or authorization path
would create architectural debt and violate the single-source-of-truth
principle established in S20.

### D2: Protocol over ABC for provider abstraction

Providers implement `ExternalInformationProvider` as a `typing.Protocol`
with `@runtime_checkable`, not as an abstract base class.

**Rationale:** Structural subtyping allows providers to be implemented
without inheriting from a NAV base class. This keeps the provider contract
lightweight and avoids coupling external integrations to NAV's internal
class hierarchy. A future third-party provider module only needs to match
the method signatures.

**Alternatives considered:**
- ABC with `abstractmethod` — rejected because it forces inheritance and
  creates a hard dependency on NAV's internal module structure.
- Duck typing without Protocol — rejected because it sacrifices static
  type checking and IDE support.

### D3: ProviderRegistry over direct injection

A `ProviderRegistry` class manages provider lifecycle, selection, and
availability checking. The capability layer queries the registry; it never
references concrete providers directly.

**Rationale:** The registry pattern supports runtime provider swapping,
multi-provider selection (future), and availability gating without
modifying the capability layer. Direct injection would require changing
the capability constructor every time a provider is added or removed.

**Alternatives considered:**
- Constructor injection of a single provider — rejected because it
  prevents multi-provider scenarios and requires re-instantiation to swap.
- Global provider singleton — rejected because it prevents testing with
  isolated provider sets and violates NAV's explicit dependency patterns.

### D4: Honesty invariant in the contract layer

`ExternalInformationResult.assert_honest()` enforces that non-success
statuses carry no items and success statuses carry at least one item.
This check lives on the result dataclass, not in the capability layer.

**Rationale:** Placing the invariant on the contract makes it enforceable
by any caller — the capability layer, tests, future S24 evidence
evaluators, or external consumers. If it lived only in the capability,
a future caller bypassing the capability could receive dishonest results.

**Alternatives considered:**
- Enforcement only in the capability layer — rejected because it creates
  a single point of enforcement that future code paths might bypass.
- Custom exception (`ProviderIntegrityError`) instead of override —
  deferred; current behavior logs CRITICAL and returns a clean error
  result to preserve the "never crash the caller" principle.

### D5: Flat RetrievalStatus enum

`RetrievalStatus` is a flat string enum with seven explicit outcomes:
`SUCCESS`, `NO_RESULTS`, `PROVIDER_ERROR`, `TIMEOUT`,
`INVALID_REQUEST`, `UNAVAILABLE`, `UNAUTHORIZED`.

**Rationale:** A flat enum makes pattern matching straightforward and
prevents ambiguous nested hierarchies (e.g., `Error.Timeout` vs
`Error.Provider.Timeout`). Every outcome is a first-class value that
callers can switch on directly.

### D6: No authorization in the capability

The `ExternalInformationCapability` contains zero authorization logic.
It does not import from `core.security` and does not define
`authorize()`, `is_allowed()`, or `check_permission()`.

**Rationale:** S20 established the Security Plane as the single
authoritative authorization boundary. Adding authorization to individual
capabilities would create a second security mechanism, violating the
S20 architecture and introducing inconsistency. If the capability is
reached, authorization has already passed upstream.

**Enforcement:** Structural test `test_capability_has_no_security_imports`
programmatically verifies this invariant on every test run.

### D7: Frozen dataclasses for all contracts

All request, result, and metadata types use `@dataclass(frozen=True)`.

**Rationale:** Immutability guarantees that contracts cannot be mutated
after creation as they flow through the dispatch chain. This prevents
a provider from modifying a request mid-flight or a caller from altering
a result after receipt.

## Consequences

### Positive

- NAV can acquire external information through a governed, replaceable
  boundary for the first time.
- New providers can be added by implementing a Protocol and registering
  with the registry — no core changes required.
- The honesty invariant prevents NAV from claiming retrieval that did
  not occur, establishing a foundation for S24 evidence semantics.
- S20 security remains the single authorization authority.

### Negative

- The first provider (Static) is intentionally narrow and not a real
  external source. A real provider must be added before production use.
- The capability is not yet wired into the live Orchestrator dispatch
  table. This requires an approved additive registration step.
- Provenance is acquisition-time only. Trust evaluation, cross-source
  consistency, and evidence reasoning are deferred to S24.

### Neutral

- The `ProviderRegistry` is currently a plain class. Its lifecycle
  management (singleton, DI container, per-request) should be aligned
  with NAV's broader capability lifecycle in a future sprint.

## Related

- ADR 0005: Security Plane
- ADR 0009: S20 Security Enforcement
- ADR 0011: S22 Status / Current Step ID
- S23 Brief §13 (Architectural Decision Rule)
- S23 Brief §14 (Security Requirements)
- S23 Brief §16 (No Fake Research)

## Files Added

- `core/contracts/external_information.py`
- `capabilities/external_information/provider_protocol.py`
- `capabilities/external_information/registry.py`
- `capabilities/external_information/static_provider.py
- capabilities/external_information/wikipedia_provider.py`
- `capabilities/external_information/capability.py`
- `tests/test_s23_external_information.py`

## Files Modified

None. NAV v1.12 baseline is frozen.
