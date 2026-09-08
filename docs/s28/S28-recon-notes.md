# S28 Reconnaissance Notes

## 1. ReasoningResult provides
- reasoning_id, question, state (ReasoningState enum)
- inputs (tuple[ReasoningInput]), steps (tuple[ReasoningStep])
- final_conclusion (str)
- supporting_input_ids, conflicting_input_ids
- limitations, finding_basis, evidence_basis, comparison_basis
- created_at, metadata

## 2. ComparisonResult provides
- comparison_id, title, state (ComparisonState)
- subjects (tuple[ComparisonSubject]), dimensions, evaluations
- summary, uncertainty, finding_basis, evidence_basis

## 3. Consumable contracts
- ReasoningResult (primary input for decision rationale)
- ComparisonResult (alternative evaluation data)
- Finding, Evidence (provenance chain)

## 4. Alternatives representation
- DecisionAlternative: id, label, description, metadata
- Minimum 1 alternative required (0 = INSUFFICIENT_INPUTS)

## 5. Objectives representation
- DecisionObjective: description, priority list
- NAV must NOT invent objectives

## 6. Constraints vs Preferences
- ConstraintType enum: HARD / SOFT
- HARD: violation disqualifies alternative
- SOFT: influences selection, can be traded off

## 7. Reusable services
- ReasoningService (consume ReasoningResult, do not duplicate)
- ComparisonService (consume ComparisonResult)
- AIGateway (core/contracts/ai.py) for model-assisted path

## 8. Deterministic paths
- Hard constraint filtering (budget, weight, etc.)
- Single-alternative auto-selection
- All-violated detection (NO_FEASIBLE_ALTERNATIVE)

## 9. Model-assisted justification
- Qualitative trade-off evaluation when multiple alternatives
  survive constraint filtering and no single winner is obvious
- Model output is untrusted; validate against known alternatives

## 10. Conventions to follow
- Frozen dataclasses with __post_init__ validation
- Tuples for collections, enums for states
- Engine(gateway=None), Service facade, Capability(Request->Response)
- _StaticGateway / _FailingGateway test doubles

## 11. Architecture support
- Clean fit: Decision consumes ReasoningResult + ComparisonResult
- No architectural change required

## 12. No architectural change needed
- Existing AIGateway, Capability, Request/Response contracts suffice
- New ADR: 0018-s28-decision-capability.md
