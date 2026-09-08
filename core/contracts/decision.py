"""
NAV v2 — S28: Decision Contracts.

Defines the structured decision boundary. Represents explicit, inspectable,
and traceable alternative selection based on objectives, constraints,
preferences, and reasoning.

Key Principles:
- S28 §6: Decision is not Reasoning. It evaluates reasoning against criteria.
- S28 §7: Decision is not Action. A decision does not authorize execution.
- S28 §12: No fake precision. Qualitative evaluation unless scoring is justified.
- S28 §13: Hard constraints vs preferences are explicitly distinguished.
- S28 §14: NAV must not invent the user's objective.
- S28 §16: Deterministic-first; model-assisted only where genuinely needed.
- S28 §17: Model output is untrusted; cannot invent alternatives or objectives.
- S28 §28: System must be capable of NOT deciding (INSUFFICIENT_INPUTS).
- Frozen dataclasses enforce immutability across capability boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class DecisionState(str, Enum):
    """
    Epistemological status of a decision result.

    DECIDED:              A single alternative is selected with justification.
    CONTESTED:            Multiple alternatives have comparable support;
                          trade-offs are documented but no clear winner emerges.
    INCONCLUSIVE:         Available reasoning/evidence is insufficient to
                          distinguish among viable alternatives.
    INSUFFICIENT_INPUTS:  Critical inputs are missing (no alternatives, no
                          objective, empty reasoning).
    NO_FEASIBLE_ALTERNATIVE: All alternatives violate at least one hard
                          constraint.
    """

    DECIDED = "decided"
    CONTESTED = "contested"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_INPUTS = "insufficient_inputs"
    NO_FEASIBLE_ALTERNATIVE = "no_feasible_alternative"


class ConstraintType(str, Enum):
    """
    Distinguishes hard constraints from soft preferences.

    HARD: Violation disqualifies the alternative entirely.
    SOFT: Influences selection but can be traded off against other criteria.
    """

    HARD = "hard"
    SOFT = "soft"


@dataclass(frozen=True)
class DecisionAlternative:
    """
    A single option under consideration.

    Attributes:
        alternative_id: Unique identifier for this alternative.
        label: Human-readable name.
        description: Optional description of the alternative.
        metadata: Optional extension data.
    """

    alternative_id: str
    label: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.alternative_id or not self.alternative_id.strip():
            raise ValueError("DecisionAlternative.alternative_id must not be empty.")
        if not self.label or not self.label.strip():
            raise ValueError("DecisionAlternative.label must not be empty.")


@dataclass(frozen=True)
class DecisionCriterion:
    """
    A single evaluation criterion (constraint or preference).

    Attributes:
        criterion_id: Unique identifier.
        name: Human-readable criterion name.
        description: Detailed description of the criterion.
        constraint_type: HARD (disqualifying) or SOFT (preferential).
        threshold: Optional qualitative or quantitative threshold description.
    """

    criterion_id: str
    name: str
    description: str = ""
    constraint_type: ConstraintType = ConstraintType.HARD
    threshold: str = ""

    def __post_init__(self) -> None:
        if not self.criterion_id or not self.criterion_id.strip():
            raise ValueError("DecisionCriterion.criterion_id must not be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("DecisionCriterion.name must not be empty.")


@dataclass(frozen=True)
class AlternativeEvaluation:
    """
    Evaluation of a single alternative against a single criterion.

    Attributes:
        alternative_id: The alternative being evaluated.
        criterion_id: The criterion applied.
        satisfies: Whether the alternative satisfies this criterion.
                   For HARD criteria, False means disqualification.
        assessment: Qualitative description of how the alternative performs.
        details: Optional supporting detail.
    """

    alternative_id: str
    criterion_id: str
    satisfies: bool
    assessment: str
    details: str = ""

    def __post_init__(self) -> None:
        if not self.alternative_id or not self.alternative_id.strip():
            raise ValueError("AlternativeEvaluation.alternative_id must not be empty.")
        if not self.criterion_id or not self.criterion_id.strip():
            raise ValueError("AlternativeEvaluation.criterion_id must not be empty.")
        if not self.assessment or not self.assessment.strip():
            raise ValueError("AlternativeEvaluation.assessment must not be empty.")


@dataclass(frozen=True)
class DecisionInput:
    """
    Complete input specification for a decision.

    Attributes:
        question: The decision question being answered.
        objective: What the decision is trying to optimize or achieve.
        alternatives: Available options (minimum 1).
        criteria: Constraints and preferences to evaluate against.
        reasoning_basis: Optional ReasoningResult IDs informing this decision.
        comparison_basis: Optional ComparisonResult IDs informing this decision.
        finding_basis: Optional Finding IDs informing this decision.
        evidence_basis: Optional Evidence IDs informing this decision.
        metadata: Optional extension data.
    """

    question: str
    objective: str
    alternatives: tuple[DecisionAlternative, ...]
    criteria: tuple[DecisionCriterion, ...] = ()
    reasoning_basis: tuple[str, ...] = ()
    comparison_basis: tuple[str, ...] = ()
    finding_basis: tuple[str, ...] = ()
    evidence_basis: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.question or not self.question.strip():
            raise ValueError("DecisionInput.question must not be empty.")
        if not self.objective or not self.objective.strip():
            raise ValueError("DecisionInput.objective must not be empty.")
        if not self.alternatives:
            raise ValueError("DecisionInput requires at least one alternative.")


@dataclass(frozen=True)
class DecisionResult:
    """
    An explicit, structured, traceable decision result.

    Preserves full lineage back to Reasoning, Comparisons, Findings,
    and Evidence.

    Attributes:
        decision_id: Unique identifier for this decision.
        question: The decision question answered.
        objective: The stated objective used for evaluation.
        state: Overall decision status.
        alternatives: All alternatives that were considered.
        criteria: All criteria applied.
        evaluations: Per-alternative, per-criterion evaluations.
        selected_alternative_id: The chosen alternative (None if no decision).
        rationale: Why the selected alternative was chosen (or why not).
        trade_offs: What is gained and lost by the selection.
        risks: Known risks affecting the decision.
        limitations: Honest gaps, uncertainties, or unaddressed factors.
        reasoning_basis: IDs of ReasoningResults consumed.
        comparison_basis: IDs of ComparisonResults consumed.
        finding_basis: IDs of Findings consumed.
        evidence_basis: IDs of Evidence items consumed.
        supporting_input_ids: IDs of inputs that support the decision.
        conflicting_input_ids: IDs of inputs that conflict with the decision.
        created_at: When the decision was generated.
        metadata: Optional extension data.
    """

    decision_id: str
    question: str
    objective: str
    state: DecisionState
    alternatives: tuple[DecisionAlternative, ...]
    criteria: tuple[DecisionCriterion, ...] = ()
    evaluations: tuple[AlternativeEvaluation, ...] = ()
    selected_alternative_id: str | None = None
    rationale: str = ""
    trade_offs: str = ""
    risks: str = ""
    limitations: str = ""
    reasoning_basis: tuple[str, ...] = ()
    comparison_basis: tuple[str, ...] = ()
    finding_basis: tuple[str, ...] = ()
    evidence_basis: tuple[str, ...] = ()
    supporting_input_ids: tuple[str, ...] = ()
    conflicting_input_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.decision_id or not self.decision_id.strip():
            raise ValueError("DecisionResult.decision_id must not be empty.")
        if not self.question or not self.question.strip():
            raise ValueError("DecisionResult.question must not be empty.")
        if not self.objective or not self.objective.strip():
            raise ValueError("DecisionResult.objective must not be empty.")
        # If DECIDED, must have a selected alternative
        if self.state == DecisionState.DECIDED and not self.selected_alternative_id:
            raise ValueError(
                "DecisionResult with state DECIDED must have a selected_alternative_id."
            )
        # If DECIDED, selected alternative must be in the alternatives list
        if self.state == DecisionState.DECIDED and self.selected_alternative_id:
            alt_ids = {a.alternative_id for a in self.alternatives}
            if self.selected_alternative_id not in alt_ids:
                raise ValueError(
                    f"selected_alternative_id '{self.selected_alternative_id}' "
                    f"not found in alternatives."
                )
        # NO_FEASIBLE_ALTERNATIVE must not have a selection
        if (
            self.state == DecisionState.NO_FEASIBLE_ALTERNATIVE
            and self.selected_alternative_id
        ):
            raise ValueError(
                "DecisionResult with state NO_FEASIBLE_ALTERNATIVE "
                "must not have a selected_alternative_id."
            )
        # INSUFFICIENT_INPUTS must not have a selection
        if (
            self.state == DecisionState.INSUFFICIENT_INPUTS
            and self.selected_alternative_id
        ):
            raise ValueError(
                "DecisionResult with state INSUFFICIENT_INPUTS "
                "must not have a selected_alternative_id."
            )
