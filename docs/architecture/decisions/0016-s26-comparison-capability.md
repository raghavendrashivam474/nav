
16. S26 Comparison Capability Foundation
Date: 2025-03

Status
Accepted

Context
NAV v2 builds intelligence capabilities through an explicit progression:
External Information (S23) -> Evidence (S24) -> Evidence Synthesis (S25) -> Comparison (S26) -> Reasoning (S27) -> Decision (S28) -> Action (S29).

S25 established deterministic Evidence Synthesis (Finding), preserving provenance back to S24 Evidence and S23 SourceMetadata.
However, NAV lacked a structured, first-class capability to evaluate how multiple evidence items, synthesized findings, claims, or alternatives relate, differ, agree, or conflict across explicit dimensions.

Without a dedicated Comparison capability:

Comparison logic would be trapped inside ad-hoc prompt templates or interaction adapters.
Lineage to underlying evidence and sources would be lost during comparative statements.
Contradictory or asymmetric evidence between options would be collapsed into unjustified certainties or arbitrary numerical scores.
Decision
Introduce Explicit Comparison Contracts (core/contracts/comparison.py):

ComparisonSubject: Explicitly labels entities being compared (EVIDENCE, FINDING, CLAIM, ALTERNATIVE).
ComparisonDimension: Represents the qualitative or evaluative basis (e.g., cost, performance, evidence_support, reliability).
ComparisonRelationship: Bounded qualitative relations (SIMILAR, DIFFERENT, FAVORED_OVER, CONTRADICTS, SUPPORTS, EQUIVALENT, INCOMPARABLE, INCONCLUSIVE).
DimensionEvaluation: Per-dimension evaluation linking favored subjects, relationship, uncertainty, and supporting evidence/finding IDs.
ComparisonResult: Comprehensive result capturing overall comparison state (CONCLUSIVE, CONTESTED, INCONCLUSIVE, INSUFFICIENT_DATA, INCOMPARABLE), full evidence basis, finding basis, dimension evaluations, uncertainty, and provenance.
Implement Deterministic + Model-Assisted Comparison Engine (capabilities/comparison/):

Deterministic Mode: Directly evaluates differences in support state, contradiction sets, and provenance breadth for Findings and Evidence without LLM dependence.
Model-Assisted Mode: Employs AIGateway with strict S8 prompt encapsulation for semantic comparison of unstructured claims or alternatives, strictly treating model outputs as analytical suggestions bounded by schema validation.
Preserve End-to-End Provenance:

Every ComparisonResult maps directly to its evidence_basis (tuple of evidence_ids) and finding_basis (tuple of finding_ids), allowing bidirectional tracing from a comparison down to S23 SourceMetadata.
Honest Conflict & Uncertainty Representation:

If evidence between alternatives is asymmetric, inconclusive, or in conflict, ComparisonState explicitly reflects CONTESTED or INCONCLUSIVE. No fake precision scores or arbitrary weights are computed.
Security & Orchestration Integration:

Exposed as ComparisonCapability registered with CapabilityRegistry and dispatched through Orchestrator under S20 / Sx1 authorization enforcement.
Consequences
Positive
Comparison becomes a verifiable, repeatable, inspectable foundation for S27 Reasoning and S28 Decision.
Complete provenance is maintained from comparisons back to raw external sources.
Does not pollute synthesis or evidence contracts; additive extension.
Negative / Trade-offs
Comparing arbitrary free-form unstructured alternatives requires careful schema parsing and fallback handling in model-assisted flows.
