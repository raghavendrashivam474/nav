"""
NAV v2 — S24: Evidence Store.

In-memory storage for evidence, relations, and evaluation history.

S24 §20: No new database or persistence architecture.
Evidence persistence is a separate architectural question for future sprints.
"""

from __future__ import annotations

from core.contracts.evidence import (
    Evidence,
    EvidenceEvaluation,
    EvidenceRelation,
    EvidenceTrace,
)


class EvidenceStore:
    """
    In-memory store for evidence items, relations, and evaluations.

    Provides traceability queries back to S23 acquisition provenance.
    """

    def __init__(self) -> None:
        self._evidence: dict[str, Evidence] = {}
        self._relations: list[EvidenceRelation] = []
        self._evaluations: list[EvidenceEvaluation] = []

    # ------------------------------------------------------------------
    # Evidence CRUD
    # ------------------------------------------------------------------

    def add_evidence(self, evidence: Evidence) -> None:
        """Store an evidence item."""
        if evidence.evidence_id in self._evidence:
            raise ValueError(
                f"Evidence already exists: {evidence.evidence_id}"
            )
        self._evidence[evidence.evidence_id] = evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Retrieve an evidence item by ID."""
        return self._evidence.get(evidence_id)

    def get_all_evidence(self) -> list[Evidence]:
        """Return all stored evidence items."""
        return list(self._evidence.values())

    def update_evidence(self, evidence: Evidence) -> None:
        """
        Replace an evidence item (e.g., after evaluation state change).

        Since Evidence is frozen, this stores the new instance under
        the same ID.
        """
        if evidence.evidence_id not in self._evidence:
            raise ValueError(
                f"Cannot update unknown evidence: {evidence.evidence_id}"
            )
        self._evidence[evidence.evidence_id] = evidence

    @property
    def evidence_count(self) -> int:
        return len(self._evidence)

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    def add_relation(self, relation: EvidenceRelation) -> None:
        """Store a relation between two evidence items."""
        # Validate both evidence items exist
        if relation.source_evidence_id not in self._evidence:
            raise ValueError(
                f"Source evidence not found: {relation.source_evidence_id}"
            )
        if relation.target_evidence_id not in self._evidence:
            raise ValueError(
                f"Target evidence not found: {relation.target_evidence_id}"
            )
        self._relations.append(relation)

    def get_relations_for(
        self, evidence_id: str
    ) -> list[EvidenceRelation]:
        """Get all relations involving a specific evidence item."""
        return [
            r
            for r in self._relations
            if r.source_evidence_id == evidence_id
            or r.target_evidence_id == evidence_id
        ]

    @property
    def relation_count(self) -> int:
        return len(self._relations)

    # ------------------------------------------------------------------
    # Evaluations
    # ------------------------------------------------------------------

    def add_evaluation(self, evaluation: EvidenceEvaluation) -> None:
        """Record an evaluation state transition."""
        self._evaluations.append(evaluation)

    def get_evaluation_history(
        self, evidence_id: str
    ) -> list[EvidenceEvaluation]:
        """Get the evaluation history for an evidence item."""
        return [
            e
            for e in self._evaluations
            if e.evidence_id == evidence_id
        ]

    # ------------------------------------------------------------------
    # Traceability
    # ------------------------------------------------------------------

    def trace(self, evidence_id: str) -> EvidenceTrace:
        """
        Build a complete provenance trace for an evidence item.

        S24 §16: Every evidence object must be traceable back to acquisition.

        Returns:
            EvidenceTrace with full provenance chain.

        Raises:
            KeyError: If the evidence ID is not found.
        """
        evidence = self._evidence.get(evidence_id)
        if evidence is None:
            raise KeyError(f"Evidence not found: {evidence_id}")

        relations = self.get_relations_for(evidence_id)

        return EvidenceTrace(
            evidence_id=evidence.evidence_id,
            claim=evidence.claim,
            source_name=evidence.source_metadata.source_name,
            source_url=evidence.source_metadata.source_url,
            provider_id=evidence.source_metadata.provider_id,
            acquisition_request_id=evidence.acquisition_request_id,
            acquisition_timestamp=evidence.acquisition_completed_at,
            original_query=evidence.source_metadata.query_echo,
            evaluation_state=evidence.evaluation_state,
            relations=relations,
        )
