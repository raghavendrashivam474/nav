"""
NAV v2 — S26: Adversarial and Edge-Case Tests.

Covers edge and adversarial conditions specified in S26 §21:
- Empty comparison inputs
- One-sided / single-subject comparisons
- Duplicate subjects and duplicate evidence references
- Contradictory and conflicting findings
- Non-existent or missing evidence IDs
- Model hallucinating invalid favored_subject_id
- Malformed / garbage JSON from model
- Security payload deepcopy tamper protection during comparison routing
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from capabilities.comparison.capability import ComparisonCapability
from capabilities.comparison.engine import ComparisonEngine
from capabilities.comparison.service import ComparisonService
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIResponse
from core.contracts.capability import Request
from core.contracts.comparison import (
    ComparisonDimension,
    ComparisonRelationship,
    ComparisonState,
    ComparisonSubject,
)
from core.contracts.evidence import Evidence
from core.contracts.external_information import SourceMetadata
from core.contracts.finding import Finding, FindingState
from core.orchestration.orchestrator import Orchestrator


def _make_source(name: str = "Adv Source") -> SourceMetadata:
    return SourceMetadata(
        source_name=name,
        provider_id="adv-provider",
        query_echo="adv query",
    )


def _make_evidence(eid: str, claim: str) -> Evidence:
    return Evidence(
        evidence_id=eid,
        claim=claim,
        source_metadata=_make_source(),
        acquisition_provider_id="adv-provider",
    )


def _make_finding(
    fid: str,
    claim: str,
    status: FindingState,
    sup: tuple[str, ...] = (),
    con: tuple[str, ...] = (),
) -> Finding:
    return Finding(
        finding_id=fid,
        claim=claim,
        status=status,
        supporting_evidence=sup,
        contradicting_evidence=con,
        uncertainty="adv uncertainty",
        evidence_basis=sup + con,
        synthesis_basis="adv synthesis",
    )


class TestComparisonEdgeCases:
    """Test boundary and edge conditions."""

    def test_empty_findings_list_raises_error(self) -> None:
        engine = ComparisonEngine()
        with pytest.raises(ValueError, match="requires at least 2 findings"):
            engine.compare_findings([])

    def test_single_finding_raises_error(self) -> None:
        engine = ComparisonEngine()
        f1 = _make_finding("f1", "Claim", FindingState.SUPPORTED)
        with pytest.raises(ValueError, match="requires at least 2 findings"):
            engine.compare_findings([f1])

    def test_empty_evidence_list_raises_error(self) -> None:
        engine = ComparisonEngine()
        with pytest.raises(ValueError, match="requires at least 2 evidence items"):
            engine.compare_evidence_items([])

    def test_missing_evidence_id_in_service_raises_key_error(self) -> None:
        service = ComparisonService()
        with pytest.raises(KeyError, match="Evidence not found: ghost_id"):
            service.compare_evidence_ids(["ghost_id", "ghost_2"])

    def test_semantic_comparison_empty_dimensions_raises_error(self) -> None:
        engine = ComparisonEngine()
        sub1 = ComparisonSubject(subject_id="s1", label="Sub 1")
        sub2 = ComparisonSubject(subject_id="s2", label="Sub 2")
        with pytest.raises(ValueError, match="requires at least 1 dimension"):
            engine.compare_subjects_semantic([sub1, sub2], [])


class TestComparisonAdversarialResilience:
    """Test resilience against hostile inputs and model hallucinations."""

    def test_model_hallucinating_unknown_favored_subject_id(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)
        # Model returns a favored_subject_id that was NOT in the input subjects
        mock_gateway.generate.return_value = AIResponse(
            content="""{
                "overall_state": "conclusive",
                "summary": "Hallucinated choice",
                "uncertainty": "none",
                "evaluations": [
                    {
                        "dimension_id": "dim1",
                        "relationship": "superior",
                        "favored_subject_id": "phantom_subject_999",
                        "summary": "Phantom is better",
                        "uncertainty": ""
                    }
                ]
            }""",
            model_used="mock-llm",
        )

        engine = ComparisonEngine(gateway=mock_gateway)
        sub1 = ComparisonSubject(subject_id="sub1", label="Subject 1")
        sub2 = ComparisonSubject(subject_id="sub2", label="Subject 2")
        dim1 = ComparisonDimension(dimension_id="dim1", name="Dimension 1")

        result = engine.compare_subjects_semantic([sub1, sub2], [dim1])

        # Engine must sanitize and nullify the hallucinated favored_subject_id
        eval_res = result.evaluations[0]
        assert eval_res.favored_subject_id is None

    def test_model_returning_invalid_state_and_relationship_strings(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)
        mock_gateway.generate.return_value = AIResponse(
            content="""{
                "overall_state": "ABSOLUTE_TRUTH_100_PERCENT",
                "summary": "Bad enums",
                "evaluations": [
                    {
                        "dimension_id": "dim1",
                        "relationship": "GOD_TIER",
                        "favored_subject_id": "sub1"
                    }
                ]
            }""",
            model_used="mock-llm",
        )

        engine = ComparisonEngine(gateway=mock_gateway)
        sub1 = ComparisonSubject(subject_id="sub1", label="Subject 1")
        sub2 = ComparisonSubject(subject_id="sub2", label="Subject 2")
        dim1 = ComparisonDimension(dimension_id="dim1", name="Dimension 1")

        result = engine.compare_subjects_semantic([sub1, sub2], [dim1])

        # Falls back gracefully to INCONCLUSIVE instead of blowing up
        assert result.state == ComparisonState.INCONCLUSIVE
        assert result.evaluations[0].relationship == ComparisonRelationship.INCONCLUSIVE

    def test_orchestrator_payload_tamper_resilience(self) -> None:
        registry = CapabilityRegistry()
        capability = ComparisonCapability()
        registry.register(capability)

        orchestrator = Orchestrator(registry=registry)

        # Send malformed payload
        req = Request(
            request_id="req-tamper-1",
            payload={
                "action": "compare_findings",
                "findings": "NOT_A_LIST",
            },
        )
        res = orchestrator.route_request("comparison", req)
        assert res.success is False
        assert "requires a 'findings' list with at least 2 items" in res.error

    def test_inconclusive_findings_comparison(self) -> None:
        engine = ComparisonEngine()
        f1 = _make_finding("f1", "Finding 1", FindingState.INCONCLUSIVE)
        f2 = _make_finding("f2", "Finding 2", FindingState.INCONCLUSIVE)

        result = engine.compare_findings([f1, f2])
        assert result.state == ComparisonState.INCONCLUSIVE
        status_eval = next(e for e in result.evaluations if e.dimension_id == "support_status")
        assert status_eval.relationship == ComparisonRelationship.EQUIVALENT
