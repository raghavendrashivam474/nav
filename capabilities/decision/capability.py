"""
NAV v2 — S28: Decision Capability.

Implements the Capability interface for Orchestrator routing and Sx1
security enforcement.
"""

from __future__ import annotations

from typing import Any

from capabilities.decision.service import DecisionService
from core.contracts.capability import Capability, Request, Response
from core.contracts.decision import (
    AlternativeEvaluation,
    ConstraintType,
    DecisionAlternative,
    DecisionCriterion,
    DecisionInput,
)
from core.log import get_logger

logger = get_logger(__name__)


class DecisionCapability(Capability):
    """
    Orchestrator-facing capability for structured decision-making.

    Actions:
    - decide: payload has "question", "objective", "alternatives",
              optional "criteria", optional "evaluations"
    """

    def __init__(self, service: DecisionService | None = None) -> None:
        self._name = "decision"
        self._version = "1.0.0"
        self._description = (
            "Explicit, inspectable, and traceable alternative selection "
            "based on objectives, constraints, preferences, and reasoning."
        )
        self._service = service or DecisionService()

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def service(self) -> DecisionService:
        return self._service

    def invoke(self, request: Request) -> Response:
        action = str(request.payload.get("action", "decide"))

        if action != "decide":
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Unknown decision action: '{action}'",
            )

        try:
            return self._handle_decide(request.request_id, request.payload)
        except Exception as exc:
            logger.error("Decision execution error: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Decision failure: {exc!s}",
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_decide(
        self, request_id: str, payload: dict[str, Any]
    ) -> Response:
        question = str(payload.get("question", "")).strip()
        objective = str(payload.get("objective", "")).strip()

        if not question:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Decision requires a non-empty 'question' in the payload.",
            )
        if not objective:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Decision requires a non-empty 'objective' in the payload.",
            )

        # Parse alternatives
        raw_alternatives = payload.get("alternatives", [])
        if not isinstance(raw_alternatives, list) or not raw_alternatives:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Decision requires a non-empty 'alternatives' list.",
            )

        alternatives: list[DecisionAlternative] = []
        for item in raw_alternatives:
            if isinstance(item, DecisionAlternative):
                alternatives.append(item)
            elif isinstance(item, dict):
                try:
                    alternatives.append(
                        DecisionAlternative(
                            alternative_id=str(item["alternative_id"]),
                            label=str(item["label"]),
                            description=str(item.get("description", "")),
                            metadata=dict(item.get("metadata", {})),
                        )
                    )
                except (KeyError, ValueError) as exc:
                    return Response(
                        request_id=request_id,
                        data={},
                        success=False,
                        error=f"Malformed alternative payload: {exc!s}",
                    )
            else:
                return Response(
                    request_id=request_id,
                    data={},
                    success=False,
                    error="Each alternative must be a dict or DecisionAlternative.",
                )

        if not alternatives:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="No valid alternatives could be constructed from payload.",
            )

        # Parse criteria (optional)
        raw_criteria = payload.get("criteria", [])
        criteria: list[DecisionCriterion] = []
        if isinstance(raw_criteria, list):
            for item in raw_criteria:
                if isinstance(item, DecisionCriterion):
                    criteria.append(item)
                elif isinstance(item, dict):
                    try:
                        criteria.append(
                            DecisionCriterion(
                                criterion_id=str(item["criterion_id"]),
                                name=str(item["name"]),
                                description=str(item.get("description", "")),
                                constraint_type=ConstraintType(
                                    item.get(
                                        "constraint_type",
                                        ConstraintType.HARD.value,
                                    )
                                ),
                                threshold=str(item.get("threshold", "")),
                            )
                        )
                    except (KeyError, ValueError) as exc:
                        return Response(
                            request_id=request_id,
                            data={},
                            success=False,
                            error=f"Malformed criterion payload: {exc!s}",
                        )

        # Parse pre-evaluations (optional)
        raw_evals = payload.get("evaluations", [])
        evaluations: list[AlternativeEvaluation] = []
        if isinstance(raw_evals, list):
            for item in raw_evals:
                if isinstance(item, AlternativeEvaluation):
                    evaluations.append(item)
                elif isinstance(item, dict):
                    try:
                        evaluations.append(
                            AlternativeEvaluation(
                                alternative_id=str(item["alternative_id"]),
                                criterion_id=str(item["criterion_id"]),
                                satisfies=bool(item.get("satisfies", True)),
                                assessment=str(
                                    item.get(
                                        "assessment",
                                        "Evaluated from payload.",
                                    )
                                ),
                                details=str(item.get("details", "")),
                            )
                        )
                    except (KeyError, ValueError) as exc:
                        return Response(
                            request_id=request_id,
                            data={},
                            success=False,
                            error=f"Malformed evaluation payload: {exc!s}",
                        )

        # Build DecisionInput
        decision_input = DecisionInput(
            question=question,
            objective=objective,
            alternatives=tuple(alternatives),
            criteria=tuple(criteria),
            reasoning_basis=tuple(payload.get("reasoning_basis", ())),
            comparison_basis=tuple(payload.get("comparison_basis", ())),
            finding_basis=tuple(payload.get("finding_basis", ())),
            evidence_basis=tuple(payload.get("evidence_basis", ())),
            metadata=dict(payload.get("metadata", {})),
        )

        result = self._service.decide(
            decision_input=decision_input,
            evaluations=evaluations if evaluations else None,
        )

        return Response(
            request_id=request_id,
            data={"decision": result},
            success=True,
        )
