# S25 Implementation Details

## Contracts (`core/contracts/finding.py`)

- `FindingState`: Enum (`SUPPORTED`, `CONTESTED`, `INCONCLUSIVE`, `INSUFFICIENT_EVIDENCE`).
- `Finding`: Frozen dataclass containing `finding_id`, `claim`, `status`, `supporting_evidence`, `contradicting_evidence`, `uncertainty`, `evidence_basis`, `derived_at`, and `synthesis_basis`.

## Engine (`capabilities/evidence/synthesis.py`)

- `EvidenceSynthesizer`: Consumes `EvidenceService`, validates evidence existence, collects internal relations, classifies evidence by relation role, deterministically determines `FindingState`, and generates structured descriptions.

## Invariant Guarantees

- **No Ghost Evidence:** Unknown or failed evidence IDs trigger `KeyError`.
- **Determinism:** Identical input produces identical `Finding` output.
- **Epistemic Humility:** Contradictions remain `CONTESTED` without arbitrary weighting.
- **Traceability:** Full chain preserved from Finding to S23 `SourceMetadata`.
