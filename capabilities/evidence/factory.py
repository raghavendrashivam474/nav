"""
NAV v2 — S24: Evidence Factory.

Transforms S23 ExternalInformationResult into S24 Evidence representations.
Validates input integrity before creating evidence.

S24 §11: FAILED retrieval → NO valid evidence payload.
"""

from __future__ import annotations

from uuid import uuid4

from core.contracts.evidence import EvaluationState, Evidence
from core.contracts.external_information import (
    ExternalInformationResult,
    RetrievalStatus,
)


class EvidenceFactory:
    """
    Creates Evidence items from S23 ExternalInformationResult.

    Preserves S23 provenance by direct reference to SourceMetadata.
    Refuses to create evidence from failed or dishonest results.
    """

    @staticmethod
    def from_result(result: ExternalInformationResult) -> list[Evidence]:
        """
        Transform a successful S23 result into a list of Evidence items.

        Args:
            result: A successful ExternalInformationResult from S23.

        Returns:
            List of Evidence items, one per ExternalInformationItem.

        Raises:
            ValueError: If the result is not successful or is dishonest.
        """
        if result.status != RetrievalStatus.SUCCESS:
            raise ValueError(
                f"Cannot create evidence from non-successful result "
                f"(status={result.status.value}). "
                "Only successful retrievals produce evidence."
            )

        if not result.has_items:
            raise ValueError(
                "Cannot create evidence from a result with no items."
            )

        # Enforce S23 honesty invariant before creating evidence
        result.assert_honest()

        evidence_items: list[Evidence] = []
        for idx, item in enumerate(result.items):
            ev = Evidence(
                evidence_id=str(uuid4()),
                claim=item.content,
                source_metadata=item.source,  # Direct reference, no duplication
                acquisition_provider_id=result.provider_id,
                acquisition_request_id=result.request_id,
                acquisition_completed_at=result.completed_at,
                item_index=idx,
                evaluation_state=EvaluationState.UNASSESSED,
            )
            evidence_items.append(ev)

        return evidence_items
