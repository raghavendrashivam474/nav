# S26 Implementation Specification — Comparison Capability

**Sprint:** S26
**Position:** First normal NAV v2 sprint after Sx1 Blackbox
**Baseline:** NAV v2.2 / S25 Evidence Synthesis
**Status:** Implemented & Verified

---

## 1. Architecture & Pipeline Positioning

S26 introduces comparative intelligence as a first-class NAV capability positioned directly between Evidence Synthesis (S25) and Reasoning (S27):

```text
S23 External Information (ExternalInformationRequest -> Provider -> ExternalInformationResult)
        ↓
S24 Evidence (Evidence, EvidenceRelation, EvidenceTrace, EvidenceService)
        ↓
S25 Evidence Synthesis (EvidenceSynthesizer -> Finding, FindingState)
        ↓
S26 Comparison [THIS SPRINT]
    ├── Deterministic Finding Comparator
    ├── Deterministic Evidence Item Comparator
    └── Model-Assisted Semantic Comparator
        ↓
S27 Reasoning [FUTURE]
        ↓
S28 Decision [FUTURE]
        ↓
S29 Action [FUTURE]
2. Comparison Contracts (core/contracts/comparison.py)
All comparison contracts are frozen dataclasses (immutable after creation) to prevent side-effects or post-instantiation parameter tampering across capability boundaries.

2.1 Enums
SubjectType
Categorizes entities undergoing comparison:

EVIDENCE: An S24 Evidence item.
FINDING: An S25 Finding synthesis artifact.
CLAIM: A raw factual assertion or statement.
ALTERNATIVE: A decision option or candidate approach.
SYSTEM_ENTITY: An internal system artifact (e.g., plan, device, provider).
ComparisonRelationship
Bounded qualitative relationship observed between compared subjects:

EQUIVALENT: Subjects are identical or indistinguishable on the evaluated dimension.
SIMILAR: Subjects share substantial alignment with minor non-conflicting variation.
DIFFERENT: Subjects exhibit meaningful divergence on the dimension.
SUPERIOR: One subject is favored over others due to stronger evidence or metrics.
INFERIOR: A subject is disfavored relative to others on the dimension.
CONTRADICTORY: Direct logical or evidential conflict exists between subjects.
COMPLEMENTARY: Subjects mutually reinforce or cover distinct non-overlapping aspects.
INCOMPARABLE: Subjects lack a shared evaluative basis on the dimension.
INCONCLUSIVE: Available information is insufficient to determine a clear relationship.
ComparisonState
Overall qualitative status of the entire comparison:

CONCLUSIVE: Evidence and findings clearly establish comparative relationships.
CONTESTED: Underlying evidence or dimensions contain unresolved contradictions.
INCONCLUSIVE: Information exists but is insufficient to establish superiority or relation.
INSUFFICIENT_DATA: Missing or empty evidence/findings for one or more subjects.
INCOMPARABLE: Subjects share no valid comparison basis or dimensions.
2.2 Dataclasses
ComparisonSubject
Represents an entity being evaluated:

subject_id: str: Unique identifier for the subject in this comparison.
label: str: Human-readable name or summary.
subject_type: SubjectType: Enum classification (default CLAIM).
reference_id: str | None: Pointer to underlying artifact (finding_id, evidence_id).
metadata: dict[str, Any]: Additional contextual attributes.
ComparisonDimension
An explicit axis or criterion:

dimension_id: str: Unique identifier for the dimension.
name: str: Human-readable dimension name (e.g., support_status, cost).
description: str: Explanation of what this dimension measures.
weight: str: Qualitative significance indicator (standard, critical, secondary).
DimensionEvaluation
Evaluation result for a single dimension across compared subjects:

dimension_id: str: Pointer to the evaluated dimension.
relationship: ComparisonRelationship: Qualitative relationship observed.
favored_subject_id: str | None: ID of the favored subject (if any).
summary: str: Qualitative explanation of the dimension evaluation.
supporting_evidence_ids: tuple[str, ...]: Provenance links to evidence items.
supporting_finding_ids: tuple[str, ...]: Provenance links to synthesized findings.
uncertainty: str: Explicit description of dimension-specific uncertainty.
ComparisonResult
Top-level immutable comparative artifact:

comparison_id: str: Unique identifier for this comparison.
title: str: Descriptive title.
state: ComparisonState: Overall qualitative status.
subjects: tuple[ComparisonSubject, ...]: All compared subjects (minimum 2).
dimensions: tuple[ComparisonDimension, ...]: All evaluated dimensions.
evaluations: tuple[DimensionEvaluation, ...]: Per-dimension evaluation results.
summary: str: High-level synthesis of comparative findings.
uncertainty: str: Honest description of limitations, missing data, or conflicts.
finding_basis: tuple[str, ...]: IDs of all S25 Findings evaluated.
evidence_basis: tuple[str, ...]: IDs of all S24 Evidence items evaluated.
created_at: datetime: UTC timestamp of comparison generation.
metadata: dict[str, Any]: Metadata for future extensibility.
3. Comparison Engine Mechanics (capabilities/comparison/engine.py)
3.1 Deterministic Finding Comparison
ComparisonEngine.compare_findings(findings: list[Finding], title: str):

Validation: Rejects sets with fewer than 2 findings.
Dimension 1 — Support Status:
Classifies findings by FindingState (SUPPORTED, CONTESTED, INCONCLUSIVE).
If one finding is SUPPORTED and the other is CONTESTED/INCONCLUSIVE, the supported finding is marked SUPERIOR.
If all are SUPPORTED or all INCONCLUSIVE, marked EQUIVALENT.
Dimension 2 — Evidence Breadth:
Compares volume of supporting evidence items (len(f.supporting_evidence)).
Flags asymmetric evidence support as SUPERIOR for the better-supported finding.
Dimension 3 — Conflict State:
Checks for presence of contradicting_evidence across findings.
If contradictions exist, overall state transitions to CONTESTED (per S26 §12).
Lineage Preservation:
Aggregates all finding_basis and underlying evidence_basis into the ComparisonResult.
3.2 Deterministic Evidence Item Comparison
ComparisonEngine.compare_evidence_items(evidence_items: list[Evidence], relations: list[EvidenceRelation]):

Provenance Dimension:
Checks source names and provider IDs.
Marks SIMILAR if originating from same source, DIFFERENT if distinct sources.
Relational Polarity Dimension:
Inspects internal graph relations (SUPPORTS, CONTRADICTS, CORROBORATES).
CONTRADICTS -> CONTRADICTORY (State: CONTESTED).
SUPPORTS / CORROBORATES -> COMPLEMENTARY (State: CONCLUSIVE).
No relations -> INCONCLUSIVE (State: INCONCLUSIVE).
3.3 Model-Assisted Semantic Comparison
ComparisonEngine.compare_subjects_semantic(subjects, dimensions, title, evidence):

Security Delimiters (S8/Sx1 Invariants):
Untrusted subjects and evidence wrapped in <untrusted_subjects> and <untrusted_evidence> XML tags.
Schema Enforcement:
Demands strict JSON conforming to ComparisonResult structure.
Hallucination Sanitization:
If model returns a favored_subject_id that does not exist in the input subjects list, it is neutralized to None.
If model returns invalid enum strings, they are mapped to INCONCLUSIVE.
Deterministic Fallback:
If AIGateway is unavailable or raises an exception, the engine falls back to a deterministic structural placeholder without raising uncaught errors.
4. Subsystem Facade & Capability Integration
4.1 Comparison Service Facade (capabilities/comparison/service.py)
Coordinates between EvidenceService and ComparisonEngine.
Provides convenience methods: compare_findings(), compare_evidence_ids(), and compare_subjects().
4.2 Comparison Capability (capabilities/comparison/capability.py)
Implements Capability abstract class (name="comparison", version="2.0.0", description, invoke).
Dispatches actions:
compare_findings: Payload contains findings list.
compare_evidence: Payload contains evidence_ids list.
compare_subjects: Payload contains subjects and dimensions lists.
Enforces strict input validation before dispatch.
4.3 Orchestrator & Security Plane Integration
Registered in CapabilityRegistry under "comparison".
Requests dispatched via Orchestrator.route_request("comparison", request).
Evaluated by SecurityService.authorize(actor, action="comparison.<action>", resource) under S20 / Sx1 rules.
Passes verified _security_actor to payload.
5. Provenance & Lineage Preservation
The comparison capability guarantees end-to-end auditability down to raw sources:

text

ComparisonResult (comparison_id, finding_basis, evidence_basis)
        ↓
    finding_basis
        ↓
S25 Finding (finding_id, evidence_basis)
        ↓
    evidence_basis
        ↓
S24 Evidence (evidence_id, source_metadata)
        ↓
S23 SourceMetadata (source_name, source_url, provider_id, query_echo, retrieved_at)
