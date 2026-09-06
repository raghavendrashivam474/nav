"""
NAV v2 — S24: Evidence Service.

Facade combining factory, evaluator, relation detector, and store.
This is the primary entry point for the Evidence subsystem.

S24 §17: Integration with S23 — additive, not rewriting.
S24 §18: Internal processing layer, not an Orchestrator-facing capability.
"""

from __future__ import annotations

from dataclasses import replace

from capabilities.evidence.evaluator import EvidenceEvaluator
from capabilities.evidence.factory import EvidenceFactory
from capabilities.evidence.relations import EvidenceRelationDetector
from capabilities.evidence.store import EvidenceStore
from core.contracts.evidence import (
    EvaluationState,
    Evidence,
    EvidenceEvaluation,
    EvidenceRelation,
    EvidenceTrace,
    RelationType,
)
from core.contracts.external_information import ExternalInformationResult


class EvidenceService:
    """
    Primary Evidence subsystem facade.

    Provides the complete S24 workflow:
    1. Ingest S23 results → Evidence
    2. Evaluate evidence
    3. Record relations
    4. Trace provenance
    """

    def __init__(self) -> None:
        self._store = EvidenceStore()
        self._factory = EvidenceFactory()
        self._evaluator = EvidenceEvaluator()
        self._detector = EvidenceRelationDetector()

    # ------------------------------------------------------------------
    # Ingestion (S23 → S24 boundary)
    # ------------------------------------------------------------------

    def ingest_result(
        self, result: ExternalInformationResult
    ) -> list[Evidence]:
        """
        Transform a successful S23 result into stored Evidence items.

        This is the primary S23 → S24 integration point.

        Args:
            result: A successful ExternalInformationResult from S23.

        Returns:
            List of Evidence items now stored in the evidence store.

        Raises:
            ValueError: If the result is not successful.
        """
        evidence_items = self._factory.from_result(result)
        for ev in evidence_items:
            self._store.add_evidence(ev)
        return evidence_items

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        evidence_id: str,
        new_state: EvaluationState,
        basis: str | None = None,
    ) -> EvidenceEvaluation:
        """
        Evaluate a stored evidence item.

        Updates the evidence in the store with the new evaluation state.

        Args:
            evidence_id: The evidence to evaluate.
            new_state: The new evaluation state.
            basis: Optional explanation.

        Returns:
            The evaluation record.

        Raises:
            KeyError: If evidence not found.
            ValueError: If transition is invalid.
        """
        evidence = self._store.get_evidence(evidence_id)
        if evidence is None:
            raise KeyError(f"Evidence not found: {evidence_id}")

        evaluation = self._evaluator.evaluate(evidence, new_state, basis)

        # Update the evidence with the new state (frozen → replace)
        updated_evidence = replace(
            evidence, evaluation_state=new_state
        )
        self._store.update_evidence(updated_evidence)
        self._store.add_evaluation(evaluation)

        return evaluation

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    def record_relation(
        self,
        source_evidence_id: str,
        target_evidence_id: str,
        relation_type: RelationType,
        basis: str | None = None,
    ) -> EvidenceRelation:
        """
        Record a relationship between two stored evidence items.

        Args:
            source_evidence_id: Subject evidence.
            target_evidence_id: Object evidence.
            relation_type: Nature of the relationship.
            basis: Optional explanation.

        Returns:
            The recorded relation.
        """
        relation = self._detector.record_relation(
            source_evidence_id,
            target_evidence_id,
            relation_type,
            basis,
        )
        self._store.add_relation(relation)
        return relation

    # ------------------------------------------------------------------
    # Traceability
    # ------------------------------------------------------------------

    def trace(self, evidence_id: str) -> EvidenceTrace:
        """
        Build a complete provenance trace for an evidence item.

        Answers: "Where did this come from and what is its status?"
        """
        return self._store.trace(evidence_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Retrieve a single evidence item."""
        return self._store.get_evidence(evidence_id)

    def get_all_evidence(self) -> list[Evidence]:
        """Retrieve all stored evidence."""
        return self._store.get_all_evidence()

    def get_relations_for(
        self, evidence_id: str
    ) -> list[EvidenceRelation]:
        """Get all relations for an evidence item."""
        return self._store.get_relations_for(evidence_id)

    def get_evaluation_history(
        self, evidence_id: str
    ) -> list[EvidenceEvaluation]:
        """Get evaluation history for an evidence item."""
        return self._store.get_evaluation_history(evidence_id)

    @property
    def evidence_count(self) -> int:
        return self._store.evidence_count

    @property
    def relation_count(self) -> int:
        return self._store.relation_count
