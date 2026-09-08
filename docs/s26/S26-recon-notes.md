# S26 Reconnaissance Notes — Comparison Foundation

**Date:** March 2025
**Baseline:** NAV v2.2 / S25 Evidence Synthesis (Commit 5579082 / Tag vx1.f)
**Status:** Completed

---

## 1. Existing Pipeline Mapping

The NAV v2 intelligence pipeline currently consists of:

```text
S23 External Information (ExternalInformationRequest -> Provider -> ExternalInformationResult + SourceMetadata)
        ↓
S24 Evidence (Evidence items, EvaluationState, EvidenceRelation, EvidenceTrace, EvidenceService, EvidenceStore)
        ↓
S25 Evidence Synthesis (EvidenceSynthesizer -> Finding, FindingState, evidence_basis, uncertainty)
        ↓
S26 Comparison [THIS SPRINT]
        ↓
S27 Reasoning [FUTURE]
        ↓
S28 Decision [FUTURE]
        ↓
S29 Action [FUTURE]
Key Assets Identified:
Contracts (core/contracts/):

core/contracts/evidence.py: Evidence, EvidenceRelation, RelationType (SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM), EvaluationState, EvidenceTrace.
core/contracts/finding.py: Finding, FindingState (SUPPORTED, CONTESTED, INCONCLUSIVE, INSUFFICIENT_EVIDENCE), evidence_basis, uncertainty, synthesis_basis.
core/contracts/security.py: ActorIdentity, ActorType, AuthorizationOutcome, SYSTEM_ACTOR.
core/contracts/capability.py: Capability, Request, Response.
core/contracts/ai.py: AIGateway, AIMessage, AIRequest, AIResponse.
Capabilities (capabilities/):

capabilities/evidence/service.py: Primary facade managing evidence storage, evaluation, and relations.
capabilities/evidence/synthesis.py: Deterministic evidence synthesizer creating Finding instances without NLP or fake precision.
capabilities/external_information/capability.py: Orchestrator-facing capability for external data acquisition.
Orchestration & Security (core/orchestration/, core/security/):

Orchestrator: Enforces identity verification, authorization checks via SecurityService, deep parameter sanitization, and dispatches to registered Capability objects.
2. Key Insights for S26 Design
Comparison is First-Class, Not Prompt Sugar:

Comparison must have explicit data contracts (ComparisonResult, ComparisonSubject, ComparisonDimension, DimensionEvaluation, ComparisonRelationship, ComparisonState).
Must preserve lineage back through Finding -> Evidence -> SourceMetadata.
Dichotomy: Deterministic vs. Semantic/Model-Assisted Comparison:

Deterministic comparison: Given structured entities (e.g. Findings with known support/contradiction sets, Evidence items, or structured dimension metrics), the comparison engine deterministically classifies asymmetries, agreements, contradictions, and data sufficiency without invoking LLMs.
Model-assisted comparison: For open qualitative alternatives or natural language claims where semantic relation is required, the comparator can consult AIGateway with strict prompt hardening (untrusted data encapsulation per S8/Sx1 principles), treating model output as analytical data rather than authoritative state.
No Fake Precision or Arbitrary Weighting:

Comparisons are qualitative and structured.
Inconclusive, contested, or incomparable states are first-class citizens.
Security Boundary:

Invocation via Orchestrator passes through SecurityService (action="comparison.<action>").
Actor identity (_security_actor) is preserved.
