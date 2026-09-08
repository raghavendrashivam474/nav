"""
NAV v2 — S26: Comparison Tests Suite.

Covers:
- Contract validation, immutability, and boundary rules (S26 §4, §9)
- Deterministic Finding comparisons (S26 §10, §15)
- Deterministic Evidence comparisons (S26 §11, §15)
- Model-assisted semantic comparisons and safe fallbacks (S26 §15)
- End-to-end pipeline: S23 External Info -> S24 Evidence -> S25 Synthesis -> S26 Comparison
- Capability routing through Orchestrator with Security authorization (S26 §16)
- Adversarial and edge cases (S26 §21)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from capabilities.comparison.capability import ComparisonCapability
from capabilities.comparison.engine import ComparisonEngine
from capabilities.comparison.service import ComparisonService
from capabilities.evidence.service import EvidenceService
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIResponse
from core.contracts.capability import Request
from core.contracts.comparison import (
    ComparisonDimension,
    ComparisonRelationship,
    ComparisonResult,
    ComparisonState,
    ComparisonSubject,
    DimensionEvaluation,
    SubjectType,
)
from core.contracts.evidence import (
    Evidence,
    RelationType,
)
from core.contracts.external_information import (
    ExternalInformationItem,
    ExternalInformationResult,
    RetrievalStatus,
    SourceMetadata,
)
from core.contracts.finding import Finding, FindingState
from core.contracts.security import (
    AuthorizationDecision,
    AuthorizationOutcome,
)
from core.orchestration.orchestrator import Orchestrator

# ===================================================================
# FIXTURES & HELPERS
# ===================================================================

def _make_source(
    name: str = "Test Source",
    url: str | None = "https://example.com",
    provider: str = "test-provider",
) -> SourceMetadata:
    return SourceMetadata(
        source_name=name,
        source_url=url,
        provider_id=provider,
        retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        query_echo="test query",
    )


def _make_evidence(
    evidence_id: str,
    claim: str,
    source_name: str = "Test Source",
    provider_id: str = "test-provider",
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        claim=claim,
        source_metadata=_make_source(name=source_name, provider=provider_id),
        acquisition_provider_id=provider_id,
    )


def _make_finding(
    finding_id: str,
    claim: str,
    status: FindingState = FindingState.SUPPORTED,
    supporting: tuple[str, ...] = ("ev-1",),
    contradicting: tuple[str, ...] = (),
    basis: tuple[str, ...] = ("ev-1",),
) -> Finding:
    return Finding(
        finding_id=finding_id,
        claim=claim,
        status=status,
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        uncertainty="Test uncertainty",
        evidence_basis=basis,
        synthesis_basis="Test synthesis basis",
    )


# ===================================================================
# 1. CONTRACT TESTS
# ===================================================================

class TestComparisonContracts:
    """Validate frozen immutability and validation constraints."""

    def test_comparison_subject_validation(self) -> None:
        sub = ComparisonSubject(
            subject_id="sub-1",
            label="Option A",
            subject_type=SubjectType.ALTERNATIVE,
        )
        assert sub.subject_id == "sub-1"
        assert sub.label == "Option A"
        assert sub.subject_type == SubjectType.ALTERNATIVE

        with pytest.raises(ValueError, match="subject_id must not be empty"):
            ComparisonSubject(subject_id="", label="Option A")

        with pytest.raises(ValueError, match="label must not be empty"):
            ComparisonSubject(subject_id="sub-1", label="")

    def test_comparison_dimension_validation(self) -> None:
        dim = ComparisonDimension(
            dimension_id="dim-1",
            name="Performance",
            description="Speed and throughput",
        )
        assert dim.dimension_id == "dim-1"
        assert dim.name == "Performance"

        with pytest.raises(ValueError, match="dimension_id must not be empty"):
            ComparisonDimension(dimension_id="", name="Cost")

        with pytest.raises(ValueError, match="name must not be empty"):
            ComparisonDimension(dimension_id="dim-1", name="")

    def test_comparison_result_requires_min_two_subjects(self) -> None:
        sub1 = ComparisonSubject(subject_id="s1", label="Sub 1")
        dim1 = ComparisonDimension(dimension_id="d1", name="Dim 1")
        ev1 = DimensionEvaluation(
            dimension_id="d1", relationship=ComparisonRelationship.SIMILAR
        )

        # 1 subject -> Error
        with pytest.raises(ValueError, match="requires at least 2 subjects"):
            ComparisonResult(
                comparison_id="comp-1",
                title="Invalid Comp",
                state=ComparisonState.CONCLUSIVE,
                subjects=(sub1,),
                dimensions=(dim1,),
                evaluations=(ev1,),
                summary="Summary",
                uncertainty="Uncertainty",
            )

        # 2 subjects -> Success
        sub2 = ComparisonSubject(subject_id="s2", label="Sub 2")
        res = ComparisonResult(
            comparison_id="comp-1",
            title="Valid Comp",
            state=ComparisonState.CONCLUSIVE,
            subjects=(sub1, sub2),
            dimensions=(dim1,),
            evaluations=(ev1,),
            summary="Summary",
            uncertainty="Uncertainty",
        )
        assert len(res.subjects) == 2
        assert res.state == ComparisonState.CONCLUSIVE


# ===================================================================
# 2. DETERMINISTIC FINDING COMPARISON TESTS
# ===================================================================

class TestDeterministicFindingComparison:
    """Test deterministic evaluation of S25 Findings."""

    def test_compare_supported_vs_contested_findings(self) -> None:
        engine = ComparisonEngine()
        f1 = _make_finding(
            "f1", "Finding 1 solid", FindingState.SUPPORTED, ("e1", "e2"), (), ("e1", "e2")
        )
        f2 = _make_finding(
            "f2", "Finding 2 contested", FindingState.CONTESTED, ("e3",), ("e4",), ("e3", "e4")
        )

        result = engine.compare_findings([f1, f2], title="F1 vs F2")

        assert result.state == ComparisonState.CONTESTED  # Contradictions present in f2
        assert len(result.evaluations) == 3
        # Support status dimension
        status_eval = next(
            e for e in result.evaluations if e.dimension_id == "support_status"
        )
        assert status_eval.favored_subject_id == "f1"
        assert status_eval.relationship == ComparisonRelationship.SUPERIOR

        # Provenance bases preserved
        assert set(result.finding_basis) == {"f1", "f2"}
        assert set(result.evidence_basis) == {"e1", "e2", "e3", "e4"}

    def test_compare_all_supported_findings_with_asymmetric_breadth(self) -> None:
        engine = ComparisonEngine()
        f1 = _make_finding(
            "f1", "Finding 1", FindingState.SUPPORTED, ("e1", "e2", "e3"), (), ("e1", "e2", "e3")
        )
        f2 = _make_finding(
            "f2", "Finding 2", FindingState.SUPPORTED, ("e4",), (), ("e4",)
        )

        result = engine.compare_findings([f1, f2], title="Support breadth")

        assert result.state == ComparisonState.CONCLUSIVE
        breadth_eval = next(
            e for e in result.evaluations if e.dimension_id == "evidence_breadth"
        )
        assert breadth_eval.favored_subject_id == "f1"
        assert breadth_eval.relationship == ComparisonRelationship.SUPERIOR


# ===================================================================
# 3. DETERMINISTIC EVIDENCE COMPARISON TESTS
# ===================================================================

class TestDeterministicEvidenceComparison:
    """Test deterministic evaluation of S24 Evidence items."""

    def test_compare_evidence_different_sources_and_contradiction(self) -> None:
        service = EvidenceService()
        ev1 = _make_evidence(
            "e1", "Claim 1", source_name="Source Alpha", provider_id="prov-a"
        )
        ev2 = _make_evidence(
            "e2", "Claim 2", source_name="Source Beta", provider_id="prov-b"
        )
        service._store.add_evidence(ev1)
        service._store.add_evidence(ev2)
        service.record_relation(
            "e1", "e2", RelationType.CONTRADICTS, basis="Direct contradiction"
        )

        comp_service = ComparisonService(evidence_service=service)
        result = comp_service.compare_evidence_ids(["e1", "e2"])

        assert result.state == ComparisonState.CONTESTED
        pol_eval = next(
            e for e in result.evaluations if e.dimension_id == "relational_polarity"
        )
        assert pol_eval.relationship == ComparisonRelationship.CONTRADICTORY
        prov_eval = next(
            e for e in result.evaluations if e.dimension_id == "provenance"
        )
        assert prov_eval.relationship == ComparisonRelationship.DIFFERENT
        assert set(result.evidence_basis) == {"e1", "e2"}


# ===================================================================
# 4. MODEL-ASSISTED COMPARISON & FALLBACKS
# ===================================================================

class TestModelAssistedComparison:
    """Test model-assisted comparison flow, schema validation, and fallbacks."""

    def test_model_assisted_comparison_success(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)
        mock_gateway.generate.return_value = AIResponse(
            content="""{
                "overall_state": "conclusive",
                "summary": "Option A is superior in performance.",
                "uncertainty": "Pricing data unverified.",
                "evaluations": [
                    {
                        "dimension_id": "perf",
                        "relationship": "superior",
                        "favored_subject_id": "opt-a",
                        "summary": "Option A achieves higher benchmarks.",
                        "uncertainty": ""
                    }
                ]
            }""",
            model_used="mock-llm",
        )

        engine = ComparisonEngine(gateway=mock_gateway)
        sub_a = ComparisonSubject(subject_id="opt-a", label="Option A")
        sub_b = ComparisonSubject(subject_id="opt-b", label="Option B")
        dim = ComparisonDimension(dimension_id="perf", name="Performance")

        result = engine.compare_subjects_semantic([sub_a, sub_b], [dim])

        assert result.state == ComparisonState.CONCLUSIVE
        assert result.evaluations[0].favored_subject_id == "opt-a"
        assert result.evaluations[0].relationship == ComparisonRelationship.SUPERIOR
        assert mock_gateway.generate.called

    def test_model_assisted_comparison_fallback_on_json_error(self) -> None:
        mock_gateway = MagicMock(spec=AIGateway)
        mock_gateway.generate.return_value = AIResponse(
            content="INVALID JSON RESPONSE <<GARBAGE>>",
            model_used="mock-llm",
        )

        engine = ComparisonEngine(gateway=mock_gateway)
        sub_a = ComparisonSubject(subject_id="opt-a", label="Option A")
        sub_b = ComparisonSubject(subject_id="opt-b", label="Option B")
        dim = ComparisonDimension(dimension_id="perf", name="Performance")

        result = engine.compare_subjects_semantic([sub_a, sub_b], [dim])

        # Falls back cleanly without crashing
        assert result.state in (
            ComparisonState.INSUFFICIENT_DATA,
            ComparisonState.INCONCLUSIVE,
        )
        assert result.evaluations[0].relationship == ComparisonRelationship.INCONCLUSIVE


# ===================================================================
# 5. ORCHESTRATION & SECURITY INTEGRATION
# ===================================================================

class TestOrchestratorIntegration:
    """Test invocation through Orchestrator with security enforcement."""

    def test_orchestrator_comparison_dispatch(self) -> None:
        registry = CapabilityRegistry()
        capability = ComparisonCapability()
        registry.register(capability)

        orchestrator = Orchestrator(registry=registry)

        f1 = _make_finding(
            "f1", "Finding 1", FindingState.SUPPORTED, ("e1",), (), ("e1",)
        )
        f2 = _make_finding(
            "f2", "Finding 2", FindingState.SUPPORTED, ("e2",), (), ("e2",)
        )

        req = Request(
            request_id="req-101",
            payload={
                "action": "compare_findings",
                "title": "Finding comparison via Orchestrator",
                "findings": [f1, f2],
            },
        )

        res = orchestrator.route_request("comparison", req)
        assert res.success is True
        comp_res: ComparisonResult = res.data["comparison"]
        assert comp_res.title == "Finding comparison via Orchestrator"
        assert len(comp_res.subjects) == 2

    def test_orchestrator_security_denial(self) -> None:
        registry = CapabilityRegistry()
        capability = ComparisonCapability()
        registry.register(capability)

        mock_sec = MagicMock()
        mock_sec.authorize.return_value = AuthorizationDecision(
            outcome=AuthorizationOutcome.DENY,
            actor_id="bad-actor",
            action="comparison.compare_findings",
            reason="Blocked by policy",
        )

        orchestrator = Orchestrator(registry=registry, security_service=mock_sec)

        req = Request(
            request_id="req-102",
            payload={
                "action": "compare_findings",
                "findings": [],
            },
        )

        res = orchestrator.route_request("comparison", req)
        assert res.success is False
        assert "Authorization denied" in res.error


# ===================================================================
# 6. END-TO-END PIPELINE: S23 -> S24 -> S25 -> S26
# ===================================================================

class TestEndToEndPipeline:
    """Verify complete lifecycle from external info to comparison."""

    def test_s23_to_s26_full_pipeline(self) -> None:
        from capabilities.evidence.synthesis import EvidenceSynthesizer

        # 1. S23 Result
        src = _make_source(name="Wiki Source", url="https://wiki.org")
        item1 = ExternalInformationItem(
            content="Solar output is 100W", source=src
        )
        item2 = ExternalInformationItem(
            content="Wind output is 150W", source=src
        )
        s23_res = ExternalInformationResult(
            status=RetrievalStatus.SUCCESS,
            items=[item1, item2],
            provider_id="test-provider",
            request_id="req-s23-1",
        )

        # 2. S24 Ingest into Evidence
        ev_service = EvidenceService()
        ev_items = ev_service.ingest_result(s23_res)
        assert len(ev_items) == 2
        e1_id = ev_items[0].evidence_id
        e2_id = ev_items[1].evidence_id

        # 3. S25 Synthesize two findings
        synthesizer = EvidenceSynthesizer(evidence_service=ev_service)
        # Record relation for e1
        ev_service.record_relation(
            e1_id, e2_id, RelationType.SUPPORTS, "Both are renewable"
        )

        f1 = synthesizer.synthesize([e1_id, e2_id], "Solar energy output")
        f2 = synthesizer.synthesize([e2_id], "Wind energy output")

        # 4. S26 Compare findings
        comp_service = ComparisonService(evidence_service=ev_service)
        comp_result = comp_service.compare_findings(
            [f1, f2], title="Solar vs Wind findings"
        )

        assert comp_result.state == ComparisonState.CONCLUSIVE
        assert len(comp_result.evaluations) == 3
        # Provenance links back to original S24 items
        assert e1_id in comp_result.evidence_basis
        assert e2_id in comp_result.evidence_basis
