"""
NAV v2 — S26: Comparison Capability.

Implements Capability interface for Orchestrator routing and S20 / Sx1
security enforcement.
"""

from __future__ import annotations

from typing import Any

from capabilities.comparison.service import ComparisonService
from core.contracts.capability import Capability, Request, Response
from core.contracts.comparison import (
    ComparisonDimension,
    ComparisonSubject,
    SubjectType,
)
from core.contracts.finding import Finding, FindingState
from core.log import get_logger

logger = get_logger(__name__)


class ComparisonCapability(Capability):
    """
    Orchestrator-facing capability for comparative evaluations.

    Actions:
    - compare_findings: payload has "findings" list of dicts or Finding objects
    - compare_evidence: payload has "evidence_ids" list of str
    - compare_subjects: payload has "subjects" list and "dimensions" list
    """

    def __init__(self, service: ComparisonService | None = None) -> None:
        self._name = "comparison"
        self._version = "2.0.0"
        self._description = (
            "Explicit, traceable comparative intelligence across findings, "
            "evidence, and alternatives."
        )
        self._service = service or ComparisonService()

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
    def service(self) -> ComparisonService:
        return self._service

    def invoke(self, request: Request) -> Response:
        action = str(request.payload.get("action", "compare_subjects"))
        title = str(request.payload.get("title", "Comparison Request"))

        try:
            if action == "compare_findings":
                return self._handle_compare_findings(
                    request.request_id, request.payload, title
                )
            elif action == "compare_evidence":
                return self._handle_compare_evidence(
                    request.request_id, request.payload, title
                )
            elif action == "compare_subjects":
                return self._handle_compare_subjects(
                    request.request_id, request.payload, title
                )
            else:
                return Response(
                    request_id=request.request_id,
                    data={},
                    success=False,
                    error=f"Unknown comparison action: '{action}'",
                )
        except Exception as exc:
            logger.error("Comparison execution error: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Comparison failure: {exc!s}",
            )

    def _handle_compare_findings(
        self, request_id: str, payload: dict[str, Any], title: str
    ) -> Response:
        raw_findings = payload.get("findings", [])
        if not isinstance(raw_findings, list) or len(raw_findings) < 2:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=(
                    "Action 'compare_findings' requires a 'findings' list "
                    "with at least 2 items."
                ),
            )

        finding_objs: list[Finding] = []
        for item in raw_findings:
            if isinstance(item, Finding):
                finding_objs.append(item)
            elif isinstance(item, dict):
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

        result = self._service.compare_findings(finding_objs, title=title)
        return Response(
            request_id=request_id,
            data={"comparison": result},
            success=True,
        )

    def _handle_compare_evidence(
        self, request_id: str, payload: dict[str, Any], title: str
    ) -> Response:
        evidence_ids = payload.get("evidence_ids", [])
        if not isinstance(evidence_ids, list) or len(evidence_ids) < 2:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=(
                    "Action 'compare_evidence' requires an 'evidence_ids' list "
                    "with at least 2 IDs."
                ),
            )

        result = self._service.compare_evidence_ids(evidence_ids, title=title)
        return Response(
            request_id=request_id,
            data={"comparison": result},
            success=True,
        )

    def _handle_compare_subjects(
        self, request_id: str, payload: dict[str, Any], title: str
    ) -> Response:
        raw_subjects = payload.get("subjects", [])
        raw_dimensions = payload.get("dimensions", [])
        evidence_ids = payload.get("evidence_ids", [])

        if not isinstance(raw_subjects, list) or len(raw_subjects) < 2:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=(
                    "Action 'compare_subjects' requires a 'subjects' list "
                    "with at least 2 subjects."
                ),
            )
        if not isinstance(raw_dimensions, list) or len(raw_dimensions) < 1:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=(
                    "Action 'compare_subjects' requires a 'dimensions' list "
                    "with at least 1 dimension."
                ),
            )

        subjects = [
            (
                s
                if isinstance(s, ComparisonSubject)
                else ComparisonSubject(
                    subject_id=str(s["subject_id"]),
                    label=str(s["label"]),
                    subject_type=SubjectType(
                        s.get("subject_type", SubjectType.CLAIM.value)
                    ),
                    reference_id=s.get("reference_id"),
                    metadata=dict(s.get("metadata", {})),
                )
            )
            for s in raw_subjects
        ]

        dimensions = [
            (
                d
                if isinstance(d, ComparisonDimension)
                else ComparisonDimension(
                    dimension_id=str(d["dimension_id"]),
                    name=str(d["name"]),
                    description=str(d.get("description", "")),
                    weight=str(d.get("weight", "standard")),
                )
            )
            for d in raw_dimensions
        ]

        result = self._service.compare_subjects(
            subjects=subjects,
            dimensions=dimensions,
            title=title,
            evidence_ids=evidence_ids if isinstance(evidence_ids, list) else None,
        )
        return Response(
            request_id=request_id,
            data={"comparison": result},
            success=True,
        )

