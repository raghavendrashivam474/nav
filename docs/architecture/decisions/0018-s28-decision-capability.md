# ADR 0018: S28 Decision Capability

## Status
Accepted

## Context
NAV v2.4 (S27 Reasoning) introduced structured inferential reasoning over Findings, Comparisons, and Evidence. Reasoning answers: "Given what we know, what follows?" However, selecting among alternatives requires evaluating those inferences against explicit objectives, constraints, preferences, and trade-offs.

## Decision
We introduce **Decision** as a first-class, model-independent capability in NAV:
1. **Separation of Concerns**: Decision is not Reasoning. Reasoning produces conclusions and justification; Decision selects among alternatives against an explicit objective.
2. **Decision ≠ Action**: A decision selects an alternative and provides structured justification. It does not execute actions or bypass human control (S29 Action boundary preserved).
3. **Deterministic-First**: Hard constraints filter disqualified alternatives deterministically before invoking any AI model. Single surviving alternatives are selected deterministically without LLM intervention.
4. **Model Safety & Sanitization**: AI Gateway is utilized only to resolve qualitative trade-offs among surviving alternatives. Hallucinated alternatives, fabricated criteria, or constraint overrides are strictly rejected with safe fallback to `CONTESTED` or `INCONCLUSIVE`.
5. **Epistemological Honesty**: No fake mathematical scoring. The system can explicitly refrain from deciding (`INSUFFICIENT_INPUTS`, `NO_FEASIBLE_ALTERNATIVE`, `CONTESTED`).

## Consequences
- Clean, traceable progression: Acquire → Synthesize → Compare → Reason → Decide → Act.
- Full provenance preserved from Evidence and Findings up through DecisionResult.
- Zero authorization/execution leakage into S28.
