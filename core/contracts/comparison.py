"""
NAV v2 — S26: Comparison Contracts.

Defines the comparative intelligence boundary. Represents structured
evaluations comparing multiple pieces of evidence, findings, claims,
or alternatives across explicit dimensions.

Key Principles:
- Comparison is explicit, structured, and traceable.
- Preserves complete provenance through finding_basis and evidence_basis.
- Distinguishes deterministic evaluations from qualitative interpretations.
- Represents conflict and uncertainty honestly without fake numerical scores.
- Frozen dataclasses enforce immutability across boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SubjectType(str, Enum):
    """Classification of entities submitted for comparison."""

    EVIDENCE = "evidence"
    FINDING = "finding"
    CLAIM = "claim"
    ALTERNATIVE = "alternative"
    SYSTEM_ENTITY = "system_entity"


class ComparisonRelationship(str, Enum):
    """
    Qualitative relationship observed between compared subjects on a dimension
    or overall.

    S26 §9: Bounded relationship set derived from evidence & synthesis models.
    """

    EQUIVALENT = "equivalent"
    SIMILAR = "similar"
    DIFFERENT = "different"
    SUPERIOR = "superior"        # Subject A favored over B on evidence or metric
    INFERIOR = "inferior"        # Subject A disfavored compared to B
    CONTRADICTORY = "contradictory"
    COMPLEMENTARY = "complementary"
    INCOMPARABLE = "incomparable"
    INCONCLUSIVE = "inconclusive"


class ComparisonState(str, Enum):
    """
    Overall qualitative state of a comparison evaluation.

    S26 §12/13: Honest state representation without artificial precision.

    CONCLUSIVE:        Evidence/findings clearly establish comparative relationships.
    CONTESTED:         Underlying evidence or dimensions contain unresolved contradictions.
    INCONCLUSIVE:      Information exists but is insufficient to determine superiority/relation.
    INSUFFICIENT_DATA: Missing or empty evidence/findings for one or more subjects.
    INCOMPARABLE:      Subjects share no valid comparison basis or dimensions.
    """

    CONCLUSIVE = "conclusive"
    CONTESTED = "contested"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_DATA = "insufficient_data"
    INCOMPARABLE = "incomparable"


@dataclass(frozen=True)
class ComparisonSubject:
    """
    Represents an entity being evaluated in a comparison.

    Attributes:
        subject_id: Identifier for this comparison subject.
        label: Human-readable name or summary of the subject.
        subject_type: Category of the subject (finding, evidence, claim, etc.).
        reference_id: Optional pointer to underlying artifact (e.g., finding_id, evidence_id).
        metadata: Additional context or attributes for the subject.
    """

    subject_id: str
    label: str
    subject_type: SubjectType = SubjectType.CLAIM
    reference_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.subject_id or not self.subject_id.strip():
            raise ValueError("ComparisonSubject.subject_id must not be empty.")
        if not self.label or not self.label.strip():
            raise ValueError("ComparisonSubject.label must not be empty.")


@dataclass(frozen=True)
class ComparisonDimension:
    """
    An explicit axis or criterion along which subjects are evaluated.

    Attributes:
        dimension_id: Unique identifier for the dimension.
        name: Name of the dimension (e.g. 'evidence_strength', 'cost', 'performance').
        description: Description of what this dimension measures.
        weight: Optional qualitative or categorical significance indicator.
    """

    dimension_id: str
    name: str
    description: str = ""
    weight: str = "standard"

    def __post_init__(self) -> None:
        if not self.dimension_id or not self.dimension_id.strip():
            raise ValueError("ComparisonDimension.dimension_id must not be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("ComparisonDimension.name must not be empty.")


@dataclass(frozen=True)
class DimensionEvaluation:
    """
    Evaluation result for a single dimension across compared subjects.

    Attributes:
        dimension_id: The dimension being evaluated.
        relationship: Observed qualitative relationship between subjects.
        favored_subject_id: ID of the favored subject, if any.
        summary: Summary explanation of the dimension evaluation.
        supporting_evidence_ids: IDs of supporting evidence used for this dimension.
        supporting_finding_ids: IDs of supporting findings used for this dimension.
        uncertainty: Description of uncertainty specific to this dimension.
    """

    dimension_id: str
    relationship: ComparisonRelationship
    favored_subject_id: str | None = None
    summary: str = ""
    supporting_evidence_ids: tuple[str, ...] = ()
    supporting_finding_ids: tuple[str, ...] = ()
    uncertainty: str = ""

    def __post_init__(self) -> None:
        if not self.dimension_id or not self.dimension_id.strip():
            raise ValueError("DimensionEvaluation.dimension_id must not be empty.")


@dataclass(frozen=True)
class ComparisonResult:
    """
    A structured, traceable comparison between two or more subjects.

    Preserves full lineage back to S25 Findings, S24 Evidence, and S23 Sources.

    Attributes:
        comparison_id: Unique identifier for this comparison result.
        title: Descriptive title of the comparison.
        state: Overall qualitative status of the comparison.
        subjects: Tuple of all compared subjects (minimum 2).
        dimensions: Tuple of all evaluation dimensions considered.
        evaluations: Tuple of per-dimension evaluation results.
        summary: High-level synthesis of comparative findings.
        uncertainty: Honest description of limitations, missing data, or conflicts.
        finding_basis: IDs of all S25 Findings evaluated.
        evidence_basis: IDs of all S24 Evidence items evaluated.
        created_at: When the comparison was generated.
        metadata: Optional metadata for extension.
    """

    comparison_id: str
    title: str
    state: ComparisonState
    subjects: tuple[ComparisonSubject, ...]
    dimensions: tuple[ComparisonDimension, ...]
    evaluations: tuple[DimensionEvaluation, ...]
    summary: str
    uncertainty: str
    finding_basis: tuple[str, ...] = ()
    evidence_basis: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.comparison_id or not self.comparison_id.strip():
            raise ValueError("ComparisonResult.comparison_id must not be empty.")
        if not self.title or not self.title.strip():
            raise ValueError("ComparisonResult.title must not be empty.")
        if len(self.subjects) < 2:
            raise ValueError("ComparisonResult requires at least 2 subjects to compare.")
