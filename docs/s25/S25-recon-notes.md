# S25 Reconnaissance Notes

## Inspected Systems

1. **S24 Evidence Contracts (`core/contracts/evidence.py`):**
   - Immutable frozen dataclasses: `Evidence`, `EvidenceRelation`, `EvidenceEvaluation`, `EvidenceTrace`.
   - `EvaluationState` is qualitative: UNASSESSED, SUPPORTED, CONTRADICTED, CONFLICTED, UNCERTAIN.
   - `RelationType`: SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM.

2. **S24 Service & Store (`capabilities/evidence/`):**
   - `EvidenceService` provides public facade with full query and relation support.
   - `EvidenceStore` provides `get_relations_for()` which queries both source and target relations.

3. **Research Subsystem (`capabilities/research/synthesis.py`):**
   - Uses LLM/AI prompt engineering + old S7/S8 `ResearchEvidence` contracts.
   - Distinct from S24/S25 deterministic evidence synthesis. No duplication or conflict.

4. **Orchestrator & Security Boundaries:**
   - Unaffected. Synthesis remains an internal data-processing capability (matches S24 ADR D5).

## Answers to Reconnaissance Questions

- **Case Classification:** Case A (purely additive).
- **Location:** `core/contracts/finding.py` and `capabilities/evidence/synthesis.py`.
- **Finding States:** `SUPPORTED`, `CONTESTED`, `INCONCLUSIVE`, `INSUFFICIENT_EVIDENCE`.
- **Persistence:** In-memory, matching S24.
