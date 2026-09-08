"""
NAV v2 — S26: Comparison Service Facade.

Primary service interface for the Comparison subsystem. Connects
Evidence and Finding retrieval to the ComparisonEngine.
"""

from __future__ import annotations

from typing import Any

from capabilities.comparison.engine import ComparisonEngine
from capabilities.evidence.service import EvidenceService
from core.contracts.ai import AIGateway
from core.contracts.comparison import (
    ComparisonDimension,
    ComparisonResult,
    ComparisonSubject,
)
from core.contracts.evidence import Evidence
from core.contracts.finding import Finding


class ComparisonService:
    """
    Subsystem facade for S26 Comparison.

    Exposes methods to compare Findings, Evidence, and arbitrary subjects/dimensions.
    """

    def __init__(
        self,
        evidence_service: EvidenceService | None = None,
        gateway: AIGateway | None = None,
    ) -> None:
        self._evidence_service = evidence_service or EvidenceService()
        self._engine = ComparisonEngine(gateway=gateway)

    @property
    def evidence_service(self) -> EvidenceService:
        return self._evidence_service

    def compare_findings(
        self,
        findings: list[Finding],
        title: str = "Finding Comparison",
    ) -> ComparisonResult:
        """Deterministically compare a set of synthesized findings."""
        return self._engine.compare_findings(findings, title=title)

    def compare_evidence_ids(
        self,
        evidence_ids: list[str],
        title: str = "Evidence Comparison",
    ) -> ComparisonResult:
        """
        Retrieve stored Evidence items by ID and perform deterministic comparison.
        """
        evidence_items: list[Evidence] = []
        for eid in evidence_ids:
            ev = self._evidence_service.get_evidence(eid)
            if ev is None:
                raise KeyError(f"Evidence not found: {eid}")
            evidence_items.append(ev)

        # Collect internal relations
        all_relations: list[Any] = []
        for eid in evidence_ids:
            all_relations.extend(self._evidence_service.get_relations_for(eid))

        return self._engine.compare_evidence_items(
            evidence_items=evidence_items,
            relations=all_relations,
            title=title,
        )

    def compare_subjects(
        self,
        subjects: list[ComparisonSubject],
        dimensions: list[ComparisonDimension],
        title: str = "Subject Comparison",
        evidence_ids: list[str] | None = None,
    ) -> ComparisonResult:
        """
        Compare arbitrary subjects across explicit dimensions with optional supporting evidence.
        """
        evidence_items: list[Evidence] = []
        if evidence_ids:
            for eid in evidence_ids:
                ev = self._evidence_service.get_evidence(eid)
                if ev is not None:
                    evidence_items.append(ev)

        return self._engine.compare_subjects_semantic(
            subjects=subjects,
            dimensions=dimensions,
            title=title,
            evidence=evidence_items if evidence_items else None,
        )
