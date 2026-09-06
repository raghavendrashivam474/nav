"""
NAV v2 — S25: Finding Contracts.

Defines the synthesis output boundary. A Finding represents a structured
conclusion derived from a bounded set of S24 Evidence items and their
explicit relationships.

IMPORTANT:
- A Finding is NOT a truth claim. It is a structured summary of what
  the evidence supports, contradicts, or leaves unresolved.
- FindingState is distinct from S24 EvaluationState (S25 §21).
- All contracts are frozen dataclasses (immutable after creation).
- Synthesis must not manufacture certainty the evidence does not justify (§5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class FindingState(str, Enum):
    """
    Bounded qualitative status of a synthesized finding.

    S25 §21: Distinct from S24 EvaluationState.
    S25 §5: Must not manufacture certainty.

    SUPPORTED:             All evidence supports; no contradictions recorded.
    CONTESTED:             Evidence contains both supporting and contradicting signals.
    INCONCLUSIVE:          Evidence exists but relationships are insufficient to conclude.
    INSUFFICIENT_EVIDENCE: No evidence was provided for synthesis.
    """

    SUPPORTED = "supported"
    CONTESTED = "contested"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class Finding:
    """
    A structured conclusion derived from a bounded set of S24 Evidence.

    Preserves full traceability back to the evidence basis and, through
    S24 EvidenceTrace, back to S23 SourceMetadata and acquisition.

    S25 §5: This is not an oracle of objective truth.
    S25 §16: Provenance must survive synthesis.
    S25 §19: Conflicts are represented, not resolved.

    Attributes:
        finding_id: Unique identifier for this finding.
        claim: The claim or question being evaluated.
        status: The synthesized status based on evidence relationships.
        supporting_evidence: IDs of evidence items with supporting relations.
        contradicting_evidence: IDs of evidence items with contradicting relations.
        uncertainty: Human-readable description of remaining uncertainty.
        evidence_basis: All evidence IDs considered during synthesis.
        derived_at: When this finding was synthesized.
        synthesis_basis: Explanation of how the finding was derived.
    """

    finding_id: str
    claim: str
    status: FindingState
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    uncertainty: str
    evidence_basis: tuple[str, ...]
    derived_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    synthesis_basis: str = ""

    def __post_init__(self) -> None:
        if not self.finding_id or not self.finding_id.strip():
            raise ValueError("Finding.finding_id must not be empty.")
        if not self.claim or not self.claim.strip():
            raise ValueError("Finding.claim must not be empty.")
