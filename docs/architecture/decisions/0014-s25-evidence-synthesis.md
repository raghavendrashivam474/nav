# ADR 0014: Evidence Synthesis and Finding Architecture

## Status

**Accepted** — S25 Implementation Complete

## Sprint

S25 — Evidence Synthesis, Conflict Resolution & Reasoned Findings (NAV v2)

## Context

S24 established the evidence representation and relational boundary (`SUPPORTS`, `CONTRADICTS`, `CORROBORATES`, `DERIVED_FROM`). S25 introduces the mechanism to answer: "Given this collection of evidence, what finding can NAV responsibly derive?"

## Decision

### D1: Case A — Purely Additive Architecture

Finding contracts are added in `core/contracts/finding.py` and the synthesis engine in `capabilities/evidence/synthesis.py`. No existing contracts or systems were modified.

### D2: Deterministic Relation-Driven Synthesis

The synthesis engine computes findings strictly from explicitly recorded `EvidenceRelation` edges. No LLM, NLP pipeline, or arbitrary numerical confidence weighting is used.

### D3: Epistemic Uncertainty Preservation

The four discrete finding states (`SUPPORTED`, `CONTESTED`, `INCONCLUSIVE`, `INSUFFICIENT_EVIDENCE`) clearly distinguish agreement from disagreement and lack of data. Supported findings explicitly state that retrieved evidence does not constitute verified truth.

### D4: Full Provenance Chain

Every finding retains an `evidence_basis` tuple of evidence IDs, enabling callers to traverse backwards through S24 `EvidenceTrace` to S23 `SourceMetadata`.

## Consequences

### Positive

- Clean, predictable, testable synthesis baseline.
- Preserves epistemic boundaries without pretending to know objective truth.
- Seamlessly integrates with S24 and S23 without breaking changes.

### Negative / Limitations

- Complex semantic reasoning across unlinked evidence is not performed automatically. Future sprints may add AI-assisted relation suggestion on top of this foundation.
