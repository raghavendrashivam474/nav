# S24 Implementation Notes

## Files Added (9 source + 7 docs)

### Contracts
- `core/contracts/evidence.py`
  - `EvaluationState` — 5-value enum
  - `RelationType` — 4-value enum (SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM)
  - `Evidence` — frozen dataclass, direct SourceMetadata reference
  - `EvidenceRelation` — frozen dataclass, links two evidence IDs
  - `EvidenceEvaluation` — frozen dataclass, records state transitions
  - `EvidenceTrace` — frozen dataclass, complete provenance chain

### Capabilities
- `capabilities/evidence/__init__.py` — Module init, exports EvidenceService
- `capabilities/evidence/factory.py` — EvidenceFactory.from_result()
  - Validates SUCCESS status and honesty before creating evidence
  - One Evidence per ExternalInformationItem
  - Preserves S23 SourceMetadata by direct reference
- `capabilities/evidence/evaluator.py` — EvidenceEvaluator.evaluate()
  - Validates state transitions against explicit transition table
  - Rejects same-state transitions
  - Returns EvidenceEvaluation record
- `capabilities/evidence/relations.py` — EvidenceRelationDetector.record_relation()
  - Creates EvidenceRelation between two evidence IDs
  - Rejects self-relations
- `capabilities/evidence/store.py` — EvidenceStore
  - In-memory dict-based storage
  - add/get/update evidence
  - add/query relations (validates both endpoints exist)
  - add/query evaluation history
  - trace() → EvidenceTrace with full provenance
- `capabilities/evidence/service.py` — EvidenceService (facade)
  - ingest_result() — S23 → S24 boundary
  - evaluate() — updates evidence state + records history
  - record_relation() — stores validated relation
  - trace() — delegates to store
  - Query methods for evidence, relations, history

### Tests
- `tests/test_s24_evidence.py` — 49 tests across 7 test classes
  - TestEvidenceConstruction (10 tests)
  - TestProvenance (7 tests)
  - TestEvaluation (9 tests)
  - TestRelationships (7 tests)
  - TestEvidenceStore (8 tests)
  - TestS23ToS24Integration (5 tests)
  - TestS23BehaviorPreserved (3 tests)

## Files Modified

**None.** All changes are purely additive (Case A).

## Provenance Strategy
```
Evidence.source_metadata ──(direct reference)──► S23 SourceMetadata
├── source_name
├── source_url
├── provider_id
├── retrieved_at
└── query_echo

Evidence (result-level)
├── acquisition_provider_id
├── acquisition_request_id
└── acquisition_completed_at

```

No fields are duplicated. If S23 SourceMetadata gains new fields in the
future, Evidence automatically inherits them through the reference.

## Evaluation Model
UNASSESSED ──► SUPPORTED / CONTRADICTED / CONFLICTED / UNCERTAIN
SUPPORTED ──► CONTRADICTED / CONFLICTED / UNCERTAIN / UNASSESSED
(reversible transitions, all states can return to UNASSESSED)

text


## Linting & Type Checking

- Ruff: 0 errors (auto-fixed import ordering)
- Mypy: Success, no issues found in 7 source files
