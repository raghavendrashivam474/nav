"""
NAV v2 — S28: Decision Service Facade.

Primary service interface for the Decision subsystem. Coordinates
Reasoning and Comparison retrieval and dispatches to the DecisionEngine.
"""

from __future__ import annotations

from capabilities.comparison.service import ComparisonService
from capabilities.decision.engine import DecisionEngine
from capabilities.evidence.service import EvidenceService
from capabilities.reasoning.service import ReasoningService
from core.contracts.ai import AIGateway
from core.contracts.decision import (
    AlternativeEvaluation,
    DecisionInput,
    DecisionResult,
)


class DecisionService:
    """
    Subsystem facade for S28 Decision.

    Provides high-level entry points for evaluating alternatives against
    objectives, constraints, and reasoning.
    """

    def __init__(
        self,
        reasoning_service: ReasoningService | None = None,
        comparison_service: ComparisonService | None = None,
        evidence_service: EvidenceService | None = None,
        gateway: AIGateway | None = None,
    ) -> None:
        self._evidence_service = evidence_service or EvidenceService()
        self._reasoning_service = reasoning_service or ReasoningService(
            evidence_service=self._evidence_service,
            comparison_service=comparison_service,
            gateway=gateway,
        )
        self._comparison_service = (
            comparison_service
            or self._reasoning_service.comparison_service
        )
        self._engine = DecisionEngine(gateway=gateway)

    @property
    def reasoning_service(self) -> ReasoningService:
        return self._reasoning_service

    @property
    def comparison_service(self) -> ComparisonService:
        return self._comparison_service

    @property
    def evidence_service(self) -> EvidenceService:
        return self._evidence_service

    def decide(
        self,
        decision_input: DecisionInput,
        evaluations: list[AlternativeEvaluation] | None = None,
    ) -> DecisionResult:
        """
        Evaluate alternatives and produce a DecisionResult.

        Args:
            decision_input: Complete decision specification.
            evaluations: Optional pre-evaluated constraint assessments.
                         If not supplied, hard constraints default to satisfied
                         unless explicitly failed.

        Returns:
            A frozen DecisionResult with full provenance.
        """
        return self._engine.decide(
            decision_input=decision_input,
            pre_evaluated_evaluations=evaluations,
        )
