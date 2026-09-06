"""
NAV v2 — S24: Evidence Relations.

Records structural relationships between evidence items.

S24 §14: Contradiction — represent disagreement without deciding truth.
S24 §15: Support/corroboration — represent independent agreement.
"""

from __future__ import annotations

from uuid import uuid4

from core.contracts.evidence import (
    EvidenceRelation,
    RelationType,
)


class EvidenceRelationDetector:
    """
    Records structural relationships between evidence items.

    Does NOT perform automatic contradiction detection or NLP analysis.
    Relationships are explicitly recorded by the caller.
    S24 provides the vocabulary and storage, not the reasoning engine.
    """

    @staticmethod
    def record_relation(
        source_evidence_id: str,
        target_evidence_id: str,
        relation_type: RelationType,
        basis: str | None = None,
    ) -> EvidenceRelation:
        """
        Record a relationship between two evidence items.

        Args:
            source_evidence_id: The subject evidence.
            target_evidence_id: The object evidence.
            relation_type: The nature of the relationship.
            basis: Optional explanation.

        Returns:
            A new EvidenceRelation.

        Raises:
            ValueError: If IDs are empty or identical.
        """
        return EvidenceRelation(
            relation_id=str(uuid4()),
            source_evidence_id=source_evidence_id,
            target_evidence_id=target_evidence_id,
            relation_type=relation_type,
            basis=basis,
        )
