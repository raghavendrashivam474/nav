"""
NAV v2 — S27: Reasoning Capability.

Implements the Capability interface for Orchestrator routing and Sx1
security enforcement.
"""

from __future__ import annotations

from typing import Any

from capabilities.reasoning.service import ReasoningService
from core.contracts.capability import Capability, Request, Response
from core.contracts.comparison import (
    ComparisonDimension,
    ComparisonResult,
    ComparisonState,
    ComparisonSubject,
    DimensionEvaluation,
    SubjectType,
)
from core.contracts.finding import Finding, FindingState
from core.contracts.reasoning import ReasoningInput, ReasoningInputType
from core.log import get_logger

logger = get_logger(__name__)


class ReasoningCapability(Capability):
    """
    Orchestrator-facing capability for structured reasoning.

    Actions:
    - reason_over_findings: payload has "question" and "findings" list
    - reason_over_comparison: payload has "question" and "comparison" dict/object
    - reason: payload has "question" and "inputs" list
    """

    def __init__(self, service: ReasoningService | None = None) -> None:
        self._name = "reasoning"
        self._version = "2.0.0"
        self._description = (
            "Explicit, inspectable, and traceable structured reasoning over "
            "evidence, findings, and comparisons."
        )
        self._service = service or ReasoningService()

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
    def service(self) -> ReasoningService:
        return self._service

    def invoke(self, request: Request) -> Response:
        action = str(request.payload.get("action", "reason"))
        question = str(request.payload.get("question", "")).strip()

        if not question:
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error="Reasoning requires a non-empty 'question' in the payload.",
            )

        try:
            if action == "reason_over_findings":
                return self._handle_reason_over_findings(
                    request.request_id, request.payload, question
                )
            elif action == "reason_over_comparison":
                return self._handle_reason_over_comparison(
                    request.request_id, request.payload, question
                )
            elif action == "reason":
                return self._handle_reason(
                    request.request_id, request.payload, question
                )
            else:
                return Response(
                    request_id=request.request_id,
                    data={},
                    success=False,
                    error=f"Unknown reasoning action: '{action}'",
                )
        except Exception as exc:
            logger.error("Reasoning execution error: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Reasoning failure: {exc!s}",
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_reason_over_findings(
        self, request_id: str, payload: dict[str, Any], question: str
    ) -> Response:
        raw_findings = payload.get("findings", [])
        if not isinstance(raw_findings, list) or not raw_findings:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=(
                    "Action 'reason_over_findings' requires a non-empty 'findings' list."
                ),
            )

        finding_objs: list[Finding] = []
        for item in raw_findings:
            if isinstance(item, Finding):
                finding_objs.append(item)
            elif isinstance(item, dict):
                try:
                    finding_objs.append(
                        Finding(
                            finding_id=str(item["finding_id"]),
                            claim=str(item["claim"]),
                            status=FindingState(
                                item.get("status", FindingState.INCONCLUSIVE.value)
                            ),
                            supporting_evidence=tuple(
                                item.get("supporting_evidence", ())
                            ),
                            contradicting_evidence=tuple(
                                item.get("contradicting_evidence", ())
                            ),
                            uncertainty=str(item.get("uncertainty", "")),
                            evidence_basis=tuple(item.get("evidence_basis", ())),
                            synthesis_basis=str(item.get("synthesis_basis", "")),
                        )
                    )
                except (KeyError, ValueError) as exc:
                    return Response(
                        request_id=request_id,
                        data={},
                        success=False,
                        error=f"Malformed finding payload: {exc!s}",
                    )

        if not finding_objs:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="No valid findings could be constructed from payload.",
            )

        result = self._service.reason_over_findings(question, finding_objs)
        return Response(
            request_id=request_id,
            data={"reasoning": result},
            success=True,
        )

    def _handle_reason_over_comparison(
        self, request_id: str, payload: dict[str, Any], question: str
    ) -> Response:
        raw_comparison = payload.get("comparison")
        if raw_comparison is None:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Action 'reason_over_comparison' requires a 'comparison' payload.",
            )

        if isinstance(raw_comparison, ComparisonResult):
            comparison_obj: ComparisonResult = raw_comparison
        elif isinstance(raw_comparison, dict):
            try:
                comparison_obj = self._parse_comparison_dict(raw_comparison)
            except (KeyError, ValueError) as exc:
                return Response(
                    request_id=request_id,
                    data={},
                    success=False,
                    error=f"Malformed comparison payload: {exc!s}",
                )
        else:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="'comparison' must be a ComparisonResult or dict.",
            )

        result = self._service.reason_over_comparison(question, comparison_obj)
        return Response(
            request_id=request_id,
            data={"reasoning": result},
            success=True,
        )

    def _handle_reason(
        self, request_id: str, payload: dict[str, Any], question: str
    ) -> Response:
        raw_inputs = payload.get("inputs", [])
        if not isinstance(raw_inputs, list) or not raw_inputs:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Action 'reason' requires a non-empty 'inputs' list.",
            )

        inputs: list[ReasoningInput] = []
        for item in raw_inputs:
            if isinstance(item, ReasoningInput):
                inputs.append(item)
            elif isinstance(item, dict):
                try:
                    inputs.append(
                        ReasoningInput(
                            input_id=str(item["input_id"]),
                            content=str(item["content"]),
                            input_type=ReasoningInputType(
                                item.get("input_type", ReasoningInputType.PREMISE.value)
                            ),
                            source_id=item.get("source_id"),
                            metadata=dict(item.get("metadata", {})),
                        )
                    )
                except (KeyError, ValueError) as exc:
                    return Response(
                        request_id=request_id,
                        data={},
                        success=False,
                        error=f"Malformed input payload: {exc!s}",
                    )

        if not inputs:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="No valid inputs could be constructed from payload.",
            )

        result = self._service.reason(question, inputs)
        return Response(
            request_id=request_id,
            data={"reasoning": result},
            success=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_comparison_dict(self, raw: dict[str, Any]) -> ComparisonResult:
        """Rebuild a minimal ComparisonResult from a dict payload."""
        subjects_raw = raw.get("subjects", [])
        dimensions_raw = raw.get("dimensions", [])
        evaluations_raw = raw.get("evaluations", [])

        subjects = tuple(
            ComparisonSubject(
                subject_id=str(s["subject_id"]),
                label=str(s["label"]),
                subject_type=SubjectType(
                    s.get("subject_type", SubjectType.CLAIM.value)
                ),
                reference_id=s.get("reference_id"),
                metadata=dict(s.get("metadata", {})),
            )
            for s in subjects_raw
        )
        dimensions = tuple(
            ComparisonDimension(
                dimension_id=str(d["dimension_id"]),
                name=str(d["name"]),
                description=str(d.get("description", "")),
                weight=str(d.get("weight", "standard")),
            )
            for d in dimensions_raw
        )
        from core.contracts.comparison import ComparisonRelationship

        evaluations = tuple(
            DimensionEvaluation(
                dimension_id=str(e["dimension_id"]),
                relationship=ComparisonRelationship(e["relationship"]),
                favored_subject_id=e.get("favored_subject_id"),
                summary=str(e.get("summary", "")),
                supporting_evidence_ids=tuple(e.get("supporting_evidence_ids", ())),
                supporting_finding_ids=tuple(e.get("supporting_finding_ids", ())),
                uncertainty=str(e.get("uncertainty", "")),
            )
            for e in evaluations_raw
        )

        return ComparisonResult(
            comparison_id=str(raw["comparison_id"]),
            title=str(raw["title"]),
            state=ComparisonState(
                raw.get("state", ComparisonState.INCONCLUSIVE.value)
            ),
            subjects=subjects,
            dimensions=dimensions,
            evaluations=evaluations,
            summary=str(raw.get("summary", "")),
            uncertainty=str(raw.get("uncertainty", "")),
            finding_basis=tuple(raw.get("finding_basis", ())),
            evidence_basis=tuple(raw.get("evidence_basis", ())),
            metadata=dict(raw.get("metadata", {})),
        )
