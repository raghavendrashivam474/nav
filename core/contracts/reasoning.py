"""
NAV v2 — S27: Reasoning Contracts.

Defines the structured reasoning boundary. Represents explicit, inspectable,
and traceable inference chains connecting Evidence, Findings, and Comparisons
to structured conclusions.

Key Principles:
- S27 §1: Reasoning is explicit, inspectable, and traceable.
- S27 §8: Reasoning produces conclusions and justification; does NOT make
  decisions (S28) or take actions (S29).
- S27 §9: Reasoning ≠ Model Output. The contract is NAV's; models are replaceable.
- S27 §18: No hidden chain-of-thought; explicit, structured steps only.
- Frozen dataclasses enforce immutability across capability boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ReasoningInputType(str, Enum):
    """Classification of knowledge items submitted to reasoning."""

    FINDING = "finding"
    EVIDENCE = "evidence"
    COMPARISON = "comparison"
    PREMISE = "premise"
    OBSERVATION = "observation"


class InferenceType(str, Enum):
    """
    Qualitative mode of inference applied in a reasoning step.

    DEDUCTIVE:   Logical derivation from established premises/findings.
    INDUCTIVE:   Pattern or trend generalization from evidence.
    ABDUCTIVE:   Inference to the most plausible explanation.
    COMPARATIVE: Relational derivation from comparative evaluations.
    ELIMINATIVE: Rule-out inference based on contradiction or disqualification.
    SYNTHETIC:   Aggregation of multiple independent inputs into a unified inference.
    """

    DEDUCTIVE = "deductive"
    INDUCTIVE = "inductive"
    ABDUCTIVE = "abductive"
    COMPARATIVE = "comparative"
    ELIMINATIVE = "eliminative"
    SYNTHETIC = "synthetic"


class ReasoningState(str, Enum):
    """
    Overall epistemological status of a reasoning result.

    SOUND:               Reasoning chain is coherent with full, uncontradicted support.
    CONTESTED:           Reasoning incorporates or exposes unresolved contradictions.
    INCONCLUSIVE:        Available inputs are insufficient to establish a definitive conclusion.
    UNSUPPORTED:         Conclusion is proposed but lacks adequate supporting premises.
    INSUFFICIENT_INPUTS: Submitted inputs are empty or unusable.
    """

    SOUND = "sound"
    CONTESTED = "contested"
    INCONCLUSIVE = "inconclusive"
    UNSUPPORTED = "unsupported"
    INSUFFICIENT_INPUTS = "insufficient_inputs"


@dataclass(frozen=True)
class ReasoningInput:
    """
    A discrete unit of knowledge submitted as basis for reasoning.

    Attributes:
        input_id: Unique identifier for this input within the reasoning context.
        content: The proposition, claim, finding text, or summary being reasoned over.
        input_type: Categorization of the input source.
        source_id: Optional reference ID to the underlying entity
                   (e.g., finding_id, evidence_id, comparison_id).
        metadata: Additional contextual attributes.
    """

    input_id: str
    content: str
    input_type: ReasoningInputType = ReasoningInputType.PREMISE
    source_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.input_id or not self.input_id.strip():
            raise ValueError("ReasoningInput.input_id must not be empty.")
        if not self.content or not self.content.strip():
            raise ValueError("ReasoningInput.content must not be empty.")


@dataclass(frozen=True)
class ReasoningStep:
    """
    A single explicit, traceable transformation or inference in the reasoning chain.

    Attributes:
        step_number: 1-based sequential position in the reasoning chain.
        inference_type: The qualitative logic applied.
        description: Human-readable explanation of this reasoning step.
        premise_ids: IDs of ReasoningInputs or prior step indices used as premises.
        intermediate_conclusion: The sub-conclusion established by this step.
        confidence_assessment: Qualitative assessment of strength
                               (e.g., 'strong', 'moderate', 'tentative').
    """

    step_number: int
    inference_type: InferenceType
    description: str
    premise_ids: tuple[str, ...] = ()
    intermediate_conclusion: str | None = None
    confidence_assessment: str = "moderate"

    def __post_init__(self) -> None:
        if self.step_number < 1:
            raise ValueError("ReasoningStep.step_number must be >= 1.")
        if not self.description or not self.description.strip():
            raise ValueError("ReasoningStep.description must not be empty.")


@dataclass(frozen=True)
class ReasoningResult:
    """
    An explicit, structured, traceable reasoning result.

    Preserves full lineage back to S25 Findings, S24 Evidence, and S26 Comparisons.

    Attributes:
        reasoning_id: Unique identifier for this reasoning result.
        question: The core question, hypothesis, or proposition reasoned about.
        state: Overall qualitative epistemological status.
        inputs: All knowledge units submitted or ingested into reasoning.
        steps: Sequential explicit reasoning steps performed.
        final_conclusion: The structured final conclusion reached.
        supporting_input_ids: IDs of ReasoningInputs that directly support the conclusion.
        conflicting_input_ids: IDs of ReasoningInputs that contradict or limit the conclusion.
        limitations: Honest description of gaps, uncertainties, or unaddressed factors.
        finding_basis: IDs of all S25 Findings evaluated.
        evidence_basis: IDs of all S24 Evidence items evaluated.
        comparison_basis: IDs of all S26 Comparisons evaluated.
        created_at: When the reasoning was generated.
        metadata: Optional metadata for extension.
    """

    reasoning_id: str
    question: str
    state: ReasoningState
    inputs: tuple[ReasoningInput, ...]
    steps: tuple[ReasoningStep, ...]
    final_conclusion: str
    supporting_input_ids: tuple[str, ...] = ()
    conflicting_input_ids: tuple[str, ...] = ()
    limitations: str = ""
    finding_basis: tuple[str, ...] = ()
    evidence_basis: tuple[str, ...] = ()
    comparison_basis: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.reasoning_id or not self.reasoning_id.strip():
            raise ValueError("ReasoningResult.reasoning_id must not be empty.")
        if not self.question or not self.question.strip():
            raise ValueError("ReasoningResult.question must not be empty.")
        if not self.final_conclusion or not self.final_conclusion.strip():
            raise ValueError("ReasoningResult.final_conclusion must not be empty.")
