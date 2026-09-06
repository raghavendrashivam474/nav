# ADR 0013: Evidence Layer Architecture

## Status

**Accepted** — S24 Implementation Complete

## Sprint

S24 — Evidence Representation, Evaluation & Traceability (NAV v2)

## Context

S23 gave NAV the ability to acquire external information through a governed,
replaceable provider boundary. The S23 contracts capture acquisition-time
provenance (SourceMetadata) and enforce honesty invariants (assert_honest).

The missing layer is the ability to:
1. Represent acquired information as structured evidence
2. Preserve and trace provenance back to acquisition
3. Evaluate evidence without conflating retrieval with truth
4. Record support and conflict relationships between evidence items

S24 must build this layer without modifying the frozen S23 architecture
or any v1 baseline systems.

## Decision

### D1: Case A — Purely additive (no architectural change)

Evidence is a new subsystem in `capabilities/evidence/` with contracts
in `core/contracts/evidence.py`. No existing file is modified.

**Rationale:** Reconnaissance confirmed the S23 architecture provides all
necessary integration points. ExternalInformationResult can be consumed
without modification. SourceMetadata provides complete provenance. No
Orchestrator, Security, or Memory changes are needed.

**Alternatives considered:**
- Embedding Evidence inside `capabilities/research/` — rejected because
  Evidence is a cross-cutting concern that may serve multiple capabilities.
- Modifying S23 contracts to include evaluation fields — rejected because
  S23 is frozen and evaluation is a separate concern from acquisition.

### D2: Direct SourceMetadata reference (no provenance duplication)

Evidence holds a direct object reference to S23 SourceMetadata rather than
copying its fields into new Evidence-specific provenance structures.

**Rationale:** Prevents provenance drift and duplication. If S23
SourceMetadata gains new fields in future sprints, Evidence automatically
benefits without requiring parallel updates.

**Alternatives considered:**
- Copying all SourceMetadata fields into Evidence — rejected because it
  creates a maintenance burden and risks inconsistency.
- Creating a new Provenance abstraction wrapping SourceMetadata — rejected
  as unnecessary indirection for S24's scope.

### D3: Qualitative evaluation over numerical trust

EvaluationState is a 5-value enum: UNASSESSED, SUPPORTED, CONTRADICTED,
CONFLICTED, UNCERTAIN. No numerical trust scores.

**Rationale:** Arbitrary numerical precision (e.g., trust = 0.87342)
without defensible semantics is worse than explicit qualitative uncertainty.
A future sprint may introduce numerical scores if a justified calculation
method emerges.

### D4: In-memory store (no persistence)

EvidenceStore uses Python dicts. No SQLite, no new database, no
modification to NAV's memory architecture.

**Rationale:** Persistence is a separate architectural question. The
evidence foundation should be validated in-memory before committing to
a persistence strategy. The store interface is clean enough to swap in
a persistent backend later.

### D5: Internal subsystem, not Orchestrator-facing

EvidenceService is not registered as an Orchestrator capability. It is
an internal processing layer used by Research/Information capabilities.

**Rationale:** Evidence is a data transformation and reasoning layer,
not a user-invocable action. Exposing it through the Orchestrator would
add public API surface without demonstrated need.

## Consequences

### Positive

- NAV can now represent acquired information as structured evidence.
- Full provenance traceability back to S23 acquisition.
- Support/conflict relationships can be recorded and queried.
- Evaluation is explicit and honest (retrieved ≠ verified).
- Zero impact on existing architecture — all 696 regression tests pass.
- Clean contracts enable future persistence and reasoning extensions.

### Negative

- Evidence is not persisted (lost on process restart).
- No automatic contradiction detection (relations are manually recorded).
- No NLP-based evidence analysis or truth resolution.

### Neutral

- The in-memory store is a deliberate simplification. A future sprint
  should evaluate persistence requirements based on actual usage patterns.

## Related

- ADR 0012: External Information Capability (S23)
- ADR 0005: Security Plane
- ADR 0009: S20 Security Enforcement
- S24 Brief §10 (Provenance), §12 (Evaluation), §13 (Trust), §20 (Memory)

## Files Added

- `core/contracts/evidence.py`
- `capabilities/evidence/__init__.py`
- `capabilities/evidence/factory.py`
- `capabilities/evidence/evaluator.py`
- `capabilities/evidence/relations.py`
- `capabilities/evidence/store.py`
- `capabilities/evidence/service.py`
- `tests/test_s24_evidence.py`

## Files Modified

None. NAV v2.0 baseline is frozen.
