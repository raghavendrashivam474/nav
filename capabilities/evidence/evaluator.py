"""
NAV v2 — S24: Evidence Evaluator.

Assigns qualitative evaluation states to evidence items.

S24 §12: Retrieved ≠ Verified. Source exists ≠ Claim is true.
S24 §13: No arbitrary numerical trust scores.
S24 §30: Do not confuse retrieved with verified.
"""

from __future__ import annotations

from core.contracts.evidence import (
    EvaluationState,
    Evidence,
    EvidenceEvaluation,
)


class EvidenceEvaluator:
    """
    Assigns bounded qualitative evaluation states to evidence.

    Does NOT determine truth. Records evaluation decisions explicitly.
    """

    # Valid transitions: from_state → set of allowed to_states
    _VALID_TRANSITIONS: dict[EvaluationState, frozenset[EvaluationState]] = {
        EvaluationState.UNASSESSED: frozenset({
            EvaluationState.SUPPORTED,
            EvaluationState.CONTRADICTED,
            EvaluationState.CONFLICTED,
            EvaluationState.UNCERTAIN,
        }),
        EvaluationState.SUPPORTED: frozenset({
            EvaluationState.CONTRADICTED,
            EvaluationState.CONFLICTED,
            EvaluationState.UNCERTAIN,
            EvaluationState.UNASSESSED,
        }),
        EvaluationState.CONTRADICTED: frozenset({
            EvaluationState.SUPPORTED,
            EvaluationState.CONFLICTED,
            EvaluationState.UNCERTAIN,
            EvaluationState.UNASSESSED,
        }),
        EvaluationState.CONFLICTED: frozenset({
            EvaluationState.SUPPORTED,
            EvaluationState.CONTRADICTED,
            EvaluationState.UNCERTAIN,
            EvaluationState.UNASSESSED,
        }),
        EvaluationState.UNCERTAIN: frozenset({
            EvaluationState.SUPPORTED,
            EvaluationState.CONTRADICTED,
            EvaluationState.CONFLICTED,
            EvaluationState.UNASSESSED,
        }),
    }

    def evaluate(
        self,
        evidence: Evidence,
        new_state: EvaluationState,
        basis: str | None = None,
    ) -> EvidenceEvaluation:
        """
        Evaluate an evidence item by assigning a new state.

        Args:
            evidence: The evidence to evaluate.
            new_state: The new evaluation state.
            basis: Optional explanation for the evaluation.

        Returns:
            An EvidenceEvaluation recording the transition.

        Raises:
            ValueError: If the transition is invalid or same-state.
        """
        if new_state == evidence.evaluation_state:
            raise ValueError(
                f"Cannot transition from {evidence.evaluation_state.value} "
                f"to the same state."
            )

        allowed = self._VALID_TRANSITIONS.get(
            evidence.evaluation_state, frozenset()
        )
        if new_state not in allowed:
            raise ValueError(
                f"Invalid evaluation transition: "
                f"{evidence.evaluation_state.value} → {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        return EvidenceEvaluation(
            evidence_id=evidence.evidence_id,
            previous_state=evidence.evaluation_state,
            new_state=new_state,
            basis=basis,
        )
