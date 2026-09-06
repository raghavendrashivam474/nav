# S24 Plan — Evidence Representation, Evaluation & Traceability

## Objective

Build the smallest durable Evidence layer that allows NAV to understand
and trace what it acquired through S23.

## Architecture Decision: Case A

Purely additive. No modifications to existing architecture.

## Components

| # | File | Purpose |
|---|------|---------|
| 1 | `core/contracts/evidence.py` | Frozen dataclass contracts |
| 2 | `capabilities/evidence/factory.py` | S23 Result → Evidence transformation |
| 3 | `capabilities/evidence/evaluator.py` | Qualitative evaluation states |
| 4 | `capabilities/evidence/relations.py` | Support/conflict representation |
| 5 | `capabilities/evidence/store.py` | In-memory evidence store + traceability |
| 6 | `capabilities/evidence/service.py` | Facade combining all components |
| 7 | `tests/test_s24_evidence.py` | 49 focused tests |

## Key Design Decisions

1. **Direct SourceMetadata reference** — Evidence holds S23 provenance by
   reference, not by copying fields. Prevents drift.
2. **Qualitative evaluation** — 5-state enum (UNASSESSED, SUPPORTED,
   CONTRADICTED, CONFLICTED, UNCERTAIN). No numerical trust scores.
3. **In-memory only** — EvidenceStore uses Python dicts. No persistence
   architecture changes.
4. **Internal subsystem** — Not registered as an Orchestrator capability.
   Used internally by Research/Information capabilities.
5. **Honest semantics** — Retrieved ≠ Verified. Default state is UNASSESSED.
   Failed S23 results cannot produce evidence.

## Integration Point
```
ExternalInformationResult (S23)
│
▼
EvidenceService.ingest_result()
│
▼
list[Evidence] (stored, traceable, evaluable)
```


## Testing Strategy

- 49 deterministic tests using S23 StaticInformationProvider
- No live network dependency for core tests
- S23 behavioral preservation tests included
- Full regression: 696 passed, 0 failed
