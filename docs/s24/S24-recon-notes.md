# S24 Recon Notes — Evidence Representation, Evaluation & Traceability

## 1. Current Architecture

NAV v2.0 (S23) provides:
- `core/contracts/external_information.py`: Frozen dataclass contracts
  - RetrievalStatus (7 states), ExternalInformationRequest, SourceMetadata,
    ExternalInformationItem, ExternalInformationResult (with assert_honest)
- `capabilities/external_information/`: Provider-based acquisition
  - Protocol-based providers (Static, Wikipedia), Registry, Capability
- `core/orchestration/orchestrator.py`: CapabilityRegistry-based dispatch with S20 security
- `capabilities/research/`: Extensive existing research infrastructure (v1 era)
  - Has its own provenance.py, retrieval.py, extraction.py, synthesis.py
  - Investigation sub-module with SQLite persistence

## 2. Relevant Existing Contracts

S23 SourceMetadata already captures: source_name, source_url, provider_id,
retrieved_at, query_echo. This is the provenance foundation S24 must reference.

S23 ExternalInformationResult captures: status, items, error_message,
provider_id, request_id, completed_at. Result-level provenance.

S23 assert_honest() invariant: non-SUCCESS → no items; SUCCESS → ≥1 items.

## 3. S23 → S24 Data Flow

ExternalInformationResult (S23)
  → EvidenceFactory (S24) validates success + honesty
  → list[Evidence] with direct SourceMetadata references (no duplication)
  → EvidenceEvaluator assigns EvaluationState
  → EvidenceRelationDetector records SUPPORTS/CONTRADICTS
  → EvidenceStore provides in-memory traceability

## 4. Smallest Insertion Point

New module: `capabilities/evidence/` (parallel to external_information)
New contract: `core/contracts/evidence.py` (parallel to external_information.py)
No modification to any existing file.

## 5. Proposed Evidence Model

- EvaluationState: UNASSESSED, SUPPORTED, CONTRADICTED, CONFLICTED, UNCERTAIN
- RelationType: SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM
- Evidence: frozen dataclass referencing S23 SourceMetadata directly
- EvidenceRelation: frozen dataclass linking two evidence IDs
- EvidenceEvaluation: frozen dataclass recording state transitions
- EvidenceTrace: frozen dataclass for provenance chain queries

## 6. Provenance Strategy

Evidence holds a direct reference to S23 SourceMetadata (no duplication).
Evidence also captures result-level fields (provider_id, request_id, completed_at).
Trace resolution walks Evidence → SourceMetadata → acquisition metadata.

## 7. Evaluation Strategy

Bounded qualitative states (no fake numerical precision).
Default state is UNASSESSED for all newly created evidence.
Evaluation is explicit and requires a basis string.
Retrieved ≠ Verified. Source exists ≠ Claim is true.

## 8. Contradiction/Support Strategy

Structural representation only — EvidenceRelation records the relationship.
No automatic truth resolution. No NLP-based contradiction detection.
Caller explicitly records relations; S24 provides the vocabulary and storage.

## 9. Persistence Decision

In-memory only for S24. EvidenceStore uses dicts.
No new database, no SQLite, no modification to memory architecture.
Documented for future S25+ persistence if needed.

## 10. Architecture Impact

ZERO impact on existing architecture.
- No S23 contract modifications
- No S23 provider modifications
- No Orchestrator modifications
- No Security modifications
- No Memory modifications
- No Research capability modifications

## 11. Architecture Decision: Case A

Existing architecture is sufficient. Evidence is implemented as a purely
additive subsystem. No architectural extensions required.
