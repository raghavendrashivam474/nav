# S28 Implementation Details

## Contracts (`core/contracts/decision.py`)
- `DecisionState`: `DECIDED`, `CONTESTED`, `INCONCLUSIVE`, `INSUFFICIENT_INPUTS`, `NO_FEASIBLE_ALTERNATIVE`.
- `ConstraintType`: `HARD` (disqualifying), `SOFT` (preferential).
- `DecisionAlternative`: Entity under evaluation with validated non-empty ID and label.
- `DecisionCriterion`: Evaluation criterion with threshold and constraint type.
- `AlternativeEvaluation`: Structured evaluation of an alternative against a criterion.
- `DecisionInput`: Validated input containing question, objective, alternatives, criteria, and provenance basis.
- `DecisionResult`: Immutable frozen result with selected alternative, rationale, trade-offs, risks, limitations, and full lineage.

## Engine (`capabilities/decision/engine.py`)
- Immediate input validation.
- Hard constraint pre-filtering.
- Deterministic single-survivor selection without AI model calls.
- AI Gateway qualitative synthesis for remaining candidates under strict schema enforcement.
- Sanitization against hallucinated alternative IDs or criterion IDs.
- Safe fallback to `CONTESTED` on model failure.

## Service & Capability (`capabilities/decision/`)
- `DecisionService`: Composes `ReasoningService`, `ComparisonService`, `EvidenceService`, and `DecisionEngine`.
- `DecisionCapability`: Implements standard NAV `Capability` interface for Orchestrator routing with action validation.
