"""
NAV v2 — S27: Reasoning Service Facade.

Primary service interface for the Reasoning subsystem. Coordinates
Evidence, Finding, and Comparison retrieval and dispatches to the
ReasoningEngine.
"""

from __future__ import annotations

from capabilities.comparison.service import ComparisonService
from capabilities.evidence.service import EvidenceService
from capabilities.reasoning.engine import ReasoningEngine
from core.contracts.ai import AIGateway
from core.contracts.comparison import ComparisonResult
from core.contracts.finding import Finding
from core.contracts.reasoning import ReasoningInput, ReasoningResult


class ReasoningService:
    """
    Subsystem facade for S27 Reasoning.

    Provides high-level entry points for reasoning over Findings, Comparisons,
    and heterogeneous premise sets.
    """

    def __init__(
        self,
        evidence_service: EvidenceService | None = None,
        comparison_service: ComparisonService | None = None,
        gateway: AIGateway | None = None,
    ) -> None:
        self._evidence_service = evidence_service or EvidenceService()
        self._comparison_service = comparison_service or ComparisonService(
            evidence_service=self._evidence_service, gateway=gateway
        )
        self._engine = ReasoningEngine(gateway=gateway)

    @property
    def evidence_service(self) -> EvidenceService:
        return self._evidence_service

    @property
    def comparison_service(self) -> ComparisonService:
        return self._comparison_service

    def reason_over_findings(
        self,
        question: str,
        findings: list[Finding],
    ) -> ReasoningResult:
        """Deterministically reason over a set of S25 Findings."""
        return self._engine.reason_over_findings(question=question, findings=findings)

    def reason_over_comparison(
        self,
        question: str,
        comparison: ComparisonResult,
    ) -> ReasoningResult:
        """Deterministically reason over an S26 ComparisonResult."""
        return self._engine.reason_over_comparison(
            question=question, comparison=comparison
        )

    def reason(
        self,
        question: str,
        inputs: list[ReasoningInput],
    ) -> ReasoningResult:
        """
        Model-assisted reasoning over heterogeneous inputs. Falls back
        deterministically when the AI gateway is unavailable or fails.
        """
        return self._engine.reason_semantic(question=question, inputs=inputs)
