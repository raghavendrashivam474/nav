"""
NAV v2 — S24: Evidence Contracts.

Defines the evidence representation, evaluation, and traceability boundary.
These contracts transform S23 ExternalInformationResult into structured evidence.

IMPORTANT:
- Evidence references S23 SourceMetadata directly (no provenance duplication).
- All contracts are frozen dataclasses (immutable after creation).
- Evaluation is qualitative, not numerical (no fake precision).
- Retrieved ≠ Verified. Source exists ≠ Claim is true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from core.contracts.external_information import SourceMetadata

# ---------------------------------------------------------------------------
# Evaluation State
# ---------------------------------------------------------------------------


class EvaluationState(str, Enum):
    """
    Bounded qualitative evaluation of an evidence item.

    S24 §12: Distinguish retrieval from evaluation.
    S24 §13: No arbitrary numerical trust scores.

    UNASSESSED:   Evidence exists but has not been evaluated.
    SUPPORTED:    Independent evidence supports this claim.
    CONTRADICTED: Independent evidence contradicts this claim.
    CONFLICTED:   Evidence has both supporting and contradicting signals.
    UNCERTAIN:    Evaluation was attempted but inconclusive.
    """

    UNASSESSED = "unassessed"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    CONFLICTED = "conflicted"
    UNCERTAIN = "uncertain"


# ---------------------------------------------------------------------------
# Relation Type
# ---------------------------------------------------------------------------


class RelationType(str, Enum):
    """
    Structural relationship between two evidence items.

    S24 §14: Contradiction handling — represent disagreement.
    S24 §15: Support/corroboration — represent agreement.
    """

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CORROBORATES = "corroborates"
    DERIVED_FROM = "derived_from"


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Evidence:
    """
    A single piece of traceable evidence derived from S23 acquisition.

    Preserves S23 provenance by direct reference to SourceMetadata.
    Captures result-level acquisition context.

    Attributes:
        evidence_id: Unique identifier for this evidence item.
        claim: The information content (from ExternalInformationItem.content).
        source_metadata: Direct reference to S23 SourceMetadata (no duplication).
        acquisition_provider_id: Provider that produced the S23 result.
        acquisition_request_id: The S23 request ID, if available.
        acquisition_completed_at: When the S23 retrieval completed.
        item_index: Position of the source item within the S23 result.
        evaluation_state: Current evaluation state (default UNASSESSED).
        created_at: When this evidence object was created.
    """

    evidence_id: str
    claim: str
    source_metadata: SourceMetadata
    acquisition_provider_id: str
    acquisition_request_id: str | None = None
    acquisition_completed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    item_index: int = 0
    evaluation_state: EvaluationState = EvaluationState.UNASSESSED
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.claim or not self.claim.strip():
            raise ValueError("Evidence.claim must not be empty.")
        if not self.evidence_id or not self.evidence_id.strip():
            raise ValueError("Evidence.evidence_id must not be empty.")
        if self.item_index < 0:
            raise ValueError("Evidence.item_index must be non-negative.")

    @property
    def source_name(self) -> str:
        """Convenience accessor for provenance traceability."""
        return self.source_metadata.source_name

    @property
    def source_url(self) -> str | None:
        """Convenience accessor for provenance traceability."""
        return self.source_metadata.source_url

    @property
    def provider_id(self) -> str:
        """Convenience accessor for the acquiring provider."""
        return self.source_metadata.provider_id


# ---------------------------------------------------------------------------
# Evidence Relation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceRelation:
    """
    A structural relationship between two evidence items.

    S24 §14: The system does not decide which claim is true.
    It records that a relationship exists.

    Attributes:
        relation_id: Unique identifier for this relation.
        source_evidence_id: The evidence that is the subject.
        target_evidence_id: The evidence that is the object.
        relation_type: The nature of the relationship.
        basis: Optional explanation of why this relation was recorded.
        created_at: When this relation was recorded.
    """

    relation_id: str
    source_evidence_id: str
    target_evidence_id: str
    relation_type: RelationType
    basis: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.source_evidence_id == self.target_evidence_id:
            raise ValueError(
                "EvidenceRelation cannot relate an evidence item to itself."
            )
        if not self.source_evidence_id.strip():
            raise ValueError("source_evidence_id must not be empty.")
        if not self.target_evidence_id.strip():
            raise ValueError("target_evidence_id must not be empty.")


# ---------------------------------------------------------------------------
# Evidence Evaluation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceEvaluation:
    """
    A record of an evaluation state transition for an evidence item.

    Attributes:
        evidence_id: The evidence being evaluated.
        previous_state: State before this evaluation.
        new_state: State after this evaluation.
        basis: Explanation for the evaluation decision.
        evaluated_at: When this evaluation was performed.
    """

    evidence_id: str
    previous_state: EvaluationState
    new_state: EvaluationState
    basis: str | None = None
    evaluated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id must not be empty.")


# ---------------------------------------------------------------------------
# Evidence Trace
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceTrace:
    """
    A complete provenance trace for an evidence item.

    Answers: "Where did this evidence come from and what is its status?"

    Attributes:
        evidence_id: The traced evidence.
        claim: The evidence content.
        source_name: Human-readable source name.
        source_url: Source locator, if available.
        provider_id: The S23 provider that acquired this.
        acquisition_request_id: The S23 request ID.
        acquisition_timestamp: When the S23 retrieval completed.
        original_query: The query that produced this evidence.
        evaluation_state: Current evaluation state.
        relations: All known relations involving this evidence.
    """

    evidence_id: str
    claim: str
    source_name: str
    source_url: str | None
    provider_id: str
    acquisition_request_id: str | None
    acquisition_timestamp: datetime
    original_query: str | None
    evaluation_state: EvaluationState
    relations: list[EvidenceRelation] = field(default_factory=list)
