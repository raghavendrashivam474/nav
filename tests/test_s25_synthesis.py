"""
NAV v2 — S25: Evidence Synthesis Tests.

Covers:
- Basic synthesis (single/multiple supporting evidence)
- Contradiction handling (support + contradiction, multiple contradictions)
- Insufficient evidence (empty set, missing IDs)
- All relation types (SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM)
- Provenance preservation through evidence_basis
- Integrity (no ghost evidence from failed acquisition)
- Determinism (same input → same output)
- Immutability (Finding is frozen)
- S24 behavior preservation (no regressions)
- S23 behavior preservation (no regressions)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from capabilities.evidence.service import EvidenceService
from capabilities.evidence.synthesis import EvidenceSynthesizer
from capabilities.external_information.capability import (
    ExternalInformationCapability,
)
from capabilities.external_information.registry import ProviderRegistry
from capabilities.external_information.static_provider import (
    StaticInformationProvider,
)
from core.contracts.evidence import (
    EvaluationState,
    Evidence,
    RelationType,
)
from core.contracts.external_information import (
    ExternalInformationItem,
    ExternalInformationRequest,
    ExternalInformationResult,
    RetrievalStatus,
    SourceMetadata,
)
from core.contracts.finding import Finding, FindingState

# ===================================================================
# HELPERS
# ===================================================================


def _make_source(
    name: str = "Test Source",
    url: str | None = "https://example.com",
    provider: str = "test-provider",
    query: str = "test query",
) -> SourceMetadata:
    return SourceMetadata(
        source_name=name,
        source_url=url,
        provider_id=provider,
        retrieved_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        query_echo=query,
    )


def _make_evidence(
    evidence_id: str,
    claim: str,
    source_name: str = "Test Source",
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        claim=claim,
        source_metadata=_make_source(name=source_name),
        acquisition_provider_id="test-provider",
    )


def _setup_service_with_evidence(
    items: list[tuple[str, str]],
) -> EvidenceService:
    """Create an EvidenceService pre-loaded with evidence items."""
    service = EvidenceService()
    for eid, claim in items:
        ev = _make_evidence(eid, claim)
        service._store.add_evidence(ev)
    return service


# ===================================================================
# BASIC SYNTHESIS TESTS
# ===================================================================


class TestBasicSynthesis:
    """S25 §30: Basic synthesis tests."""

    def test_single_supporting_evidence(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "X occurred in 2020."),
            ("ev-2", "X occurred in 2020 as well."),
        ])
        service.record_relation(
            "ev-1", "ev-2", RelationType.SUPPORTS, "Same claim."
        )
        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(["ev-1", "ev-2"], "X occurred in 2020.")

        assert finding.status == FindingState.SUPPORTED
        assert "ev-1" in finding.supporting_evidence
        assert "ev-2" in finding.supporting_evidence
        assert len(finding.contradicting_evidence) == 0
        assert finding.claim == "X occurred in 2020."

    def test_multiple_supporting_evidence(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "Claim X."),
            ("ev-2", "Claim X confirmed."),
            ("ev-3", "Claim X corroborated."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.SUPPORTS)
        service.record_relation("ev-1", "ev-3", RelationType.CORROBORATES)

        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(
            ["ev-1", "ev-2", "ev-3"], "Claim X."
        )

        assert finding.status == FindingState.SUPPORTED
        assert len(finding.supporting_evidence) == 3
        assert len(finding.contradicting_evidence) == 0

    def test_single_evidence_no_relations_is_inconclusive(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "Lone claim."),
        ])
        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(["ev-1"], "Lone claim.")

        assert finding.status == FindingState.INCONCLUSIVE
        assert len(finding.supporting_evidence) == 0
        assert len(finding.contradicting_evidence) == 0
        assert "ev-1" in finding.evidence_basis

    def test_multiple_evidence_no_relations_is_inconclusive(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "Claim A."),
            ("ev-2", "Claim B."),
        ])
        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(["ev-1", "ev-2"], "Some claim.")

        assert finding.status == FindingState.INCONCLUSIVE


# ===================================================================
# CONTRADICTION TESTS
# ===================================================================


class TestContradictionHandling:
    """S25 §19, §30: Contradiction handling tests."""

    def test_support_plus_contradiction_is_contested(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-a", "X occurred in 2020."),
            ("ev-b", "X also in 2020."),
            ("ev-c", "X occurred in 2021."),
        ])
        service.record_relation("ev-a", "ev-b", RelationType.SUPPORTS)
        service.record_relation("ev-c", "ev-a", RelationType.CONTRADICTS)

        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(
            ["ev-a", "ev-b", "ev-c"], "X date."
        )

        assert finding.status == FindingState.CONTESTED
        assert len(finding.supporting_evidence) == 2
        assert len(finding.contradicting_evidence) == 2

    def test_pure_contradiction_is_contested(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "X is true."),
            ("ev-2", "X is false."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.CONTRADICTS)

        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(["ev-1", "ev-2"], "Is X true?")

        assert finding.status == FindingState.CONTESTED
        assert "ev-1" in finding.contradicting_evidence
        assert "ev-2" in finding.contradicting_evidence

    def test_conflict_not_resolved(self) -> None:
        """S25 §19: The system must not arbitrarily choose a side."""
        service = _setup_service_with_evidence([
            ("ev-1", "X occurred in 2020."),
            ("ev-2", "X occurred in 2021."),
        ])
        service.record_relation(
            "ev-1", "ev-2", RelationType.CONTRADICTS, "Different dates."
        )

        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(
            ["ev-1", "ev-2"], "When did X occur?"
        )

        assert finding.status == FindingState.CONTESTED
        assert "unresolved" in finding.uncertainty.lower()

    def test_multiple_contradictions(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "Claim A."),
            ("ev-2", "Not A."),
            ("ev-3", "Also not A."),
        ])
        service.record_relation("ev-2", "ev-1", RelationType.CONTRADICTS)
        service.record_relation("ev-3", "ev-1", RelationType.CONTRADICTS)

        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize(
            ["ev-1", "ev-2", "ev-3"], "Is A true?"
        )

        assert finding.status == FindingState.CONTESTED


# ===================================================================
# INSUFFICIENT EVIDENCE TESTS
# ===================================================================


class TestInsufficientEvidence:
    """S25 §18, §30: Insufficient evidence tests."""

    def test_empty_evidence_list(self) -> None:
        service = EvidenceService()
        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize([], "Any claim.")

        assert finding.status == FindingState.INSUFFICIENT_EVIDENCE
        assert len(finding.evidence_basis) == 0
        assert len(finding.supporting_evidence) == 0
        assert len(finding.contradicting_evidence) == 0

    def test_missing_evidence_id_raises(self) -> None:
        """S25 §17: No ghost evidence."""
        service = EvidenceService()
        synthesizer = EvidenceSynthesizer(service)

        with pytest.raises(KeyError, match="not found"):
            synthesizer.synthesize(["nonexistent-id"], "Claim.")

    def test_partial_missing_evidence_raises(self) -> None:
        service = _setup_service_with_evidence([("ev-1", "Valid.")])
        synthesizer = EvidenceSynthesizer(service)

        with pytest.raises(KeyError, match="not found"):
            synthesizer.synthesize(["ev-1", "ghost-id"], "Claim.")

    def test_empty_claim_rejected(self) -> None:
        service = EvidenceService()
        synthesizer = EvidenceSynthesizer(service)

        with pytest.raises(ValueError, match="claim must not be empty"):
            synthesizer.synthesize([], "")

    def test_whitespace_claim_rejected(self) -> None:
        service = EvidenceService()
        synthesizer = EvidenceSynthesizer(service)

        with pytest.raises(ValueError, match="claim must not be empty"):
            synthesizer.synthesize([], "   ")


# ===================================================================
# RELATIONSHIP TYPE TESTS
# ===================================================================


class TestRelationTypes:
    """S25 §30: All relation types handled correctly."""

    def test_supports_relation(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "A."), ("ev-2", "A confirmed."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.SUPPORTS)

        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1", "ev-2"], "A."
        )
        assert finding.status == FindingState.SUPPORTED

    def test_corroborates_relation(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "B."), ("ev-2", "B independently."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.CORROBORATES)

        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1", "ev-2"], "B."
        )
        assert finding.status == FindingState.SUPPORTED

    def test_contradicts_relation(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "C."), ("ev-2", "Not C."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.CONTRADICTS)

        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1", "ev-2"], "C."
        )
        assert finding.status == FindingState.CONTESTED

    def test_derived_from_does_not_affect_status(self) -> None:
        """DERIVED_FROM is informational, not a support/contradiction signal."""
        service = _setup_service_with_evidence([
            ("ev-1", "Original."), ("ev-2", "Derived."),
        ])
        service.record_relation("ev-2", "ev-1", RelationType.DERIVED_FROM)

        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1", "ev-2"], "Original."
        )
        # DERIVED_FROM alone should not produce SUPPORTED
        assert finding.status == FindingState.INCONCLUSIVE
        assert "1 derived-from" in finding.synthesis_basis


# ===================================================================
# PROVENANCE TESTS
# ===================================================================


class TestProvenance:
    """S25 §16, §30: Provenance preservation tests."""

    def test_evidence_basis_contains_all_input_ids(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "A."), ("ev-2", "B."), ("ev-3", "C."),
        ])
        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1", "ev-2", "ev-3"], "Topic."
        )
        assert set(finding.evidence_basis) == {"ev-1", "ev-2", "ev-3"}

    def test_evidence_basis_is_sorted(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-c", "C."), ("ev-a", "A."), ("ev-b", "B."),
        ])
        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-c", "ev-a", "ev-b"], "Topic."
        )
        assert finding.evidence_basis == ("ev-a", "ev-b", "ev-c")

    def test_finding_traces_to_s24_evidence(self) -> None:
        """S25 §16: Finding → Evidence → SourceMetadata → Acquisition."""
        service = _setup_service_with_evidence([
            ("ev-1", "Traceable claim."),
        ])
        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1"], "Traceable claim."
        )

        # Verify we can trace from finding back to evidence
        for eid in finding.evidence_basis:
            ev = service.get_evidence(eid)
            assert ev is not None
            assert ev.source_metadata is not None
            assert ev.source_name == "Test Source"

    def test_finding_traces_to_s23_provenance(self) -> None:
        """Full chain: Finding → Evidence → SourceMetadata."""
        service = _setup_service_with_evidence([
            ("ev-1", "Full trace."),
        ])
        finding = EvidenceSynthesizer(service).synthesize(
            ["ev-1"], "Full trace."
        )

        ev = service.get_evidence(finding.evidence_basis[0])
        assert ev is not None
        trace = service.trace(ev.evidence_id)
        assert trace.source_name == "Test Source"
        assert trace.provider_id == "test-provider"


# ===================================================================
# INTEGRITY TESTS
# ===================================================================


class TestIntegrity:
    """S25 §17, §30: No ghost evidence."""

    def test_failed_acquisition_cannot_enter_synthesis(self) -> None:
        """S25 §17: Failed S23 → no S24 evidence → no S25 finding."""
        registry = ProviderRegistry()
        registry.register(StaticInformationProvider(), set_default=True)
        capability = ExternalInformationCapability(registry)
        service = EvidenceService()

        # Failed acquisition
        req = ExternalInformationRequest(query="completely unknown xyz")
        result = capability.acquire(req)
        assert result.status == RetrievalStatus.NO_RESULTS

        # Cannot ingest → no evidence exists
        with pytest.raises(ValueError, match="non-successful"):
            service.ingest_result(result)

        # Synthesizer has no evidence to work with
        synthesizer = EvidenceSynthesizer(service)
        finding = synthesizer.synthesize([], "Unknown topic.")
        assert finding.status == FindingState.INSUFFICIENT_EVIDENCE


# ===================================================================
# DETERMINISM TESTS
# ===================================================================


class TestDeterminism:
    """S25 §12, §30: Same input → same output."""

    def test_same_input_same_status(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "X."), ("ev-2", "X confirmed."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.SUPPORTS)
        synthesizer = EvidenceSynthesizer(service)

        f1 = synthesizer.synthesize(["ev-1", "ev-2"], "X.")
        f2 = synthesizer.synthesize(["ev-1", "ev-2"], "X.")

        assert f1.status == f2.status
        assert f1.supporting_evidence == f2.supporting_evidence
        assert f1.contradicting_evidence == f2.contradicting_evidence
        assert f1.evidence_basis == f2.evidence_basis
        assert f1.uncertainty == f2.uncertainty
        assert f1.synthesis_basis == f2.synthesis_basis
        assert f1.claim == f2.claim

    def test_same_input_same_contested(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-1", "A."), ("ev-2", "Not A."),
        ])
        service.record_relation("ev-1", "ev-2", RelationType.CONTRADICTS)
        synthesizer = EvidenceSynthesizer(service)

        f1 = synthesizer.synthesize(["ev-1", "ev-2"], "A?")
        f2 = synthesizer.synthesize(["ev-1", "ev-2"], "A?")

        assert f1.status == f2.status == FindingState.CONTESTED
        assert f1.supporting_evidence == f2.supporting_evidence
        assert f1.contradicting_evidence == f2.contradicting_evidence

    def test_duplicate_ids_deduplicated(self) -> None:
        service = _setup_service_with_evidence([("ev-1", "X.")])
        synthesizer = EvidenceSynthesizer(service)

        finding = synthesizer.synthesize(
            ["ev-1", "ev-1", "ev-1"], "X."
        )
        assert finding.evidence_basis == ("ev-1",)


# ===================================================================
# IMMUTABILITY TESTS
# ===================================================================


class TestImmutability:
    """S25 §30: Finding contracts are frozen."""

    def test_finding_is_frozen(self) -> None:
        service = _setup_service_with_evidence([("ev-1", "X.")])
        finding = EvidenceSynthesizer(service).synthesize(["ev-1"], "X.")

        with pytest.raises(AttributeError):
            finding.status = FindingState.CONTESTED  # type: ignore[misc]

    def test_finding_claim_is_frozen(self) -> None:
        service = _setup_service_with_evidence([("ev-1", "X.")])
        finding = EvidenceSynthesizer(service).synthesize(["ev-1"], "X.")

        with pytest.raises(AttributeError):
            finding.claim = "Modified"  # type: ignore[misc]

    def test_finding_id_validation(self) -> None:
        with pytest.raises(ValueError, match="finding_id"):
            Finding(
                finding_id="",
                claim="Valid claim.",
                status=FindingState.SUPPORTED,
                supporting_evidence=(),
                contradicting_evidence=(),
                uncertainty="None.",
                evidence_basis=(),
            )

    def test_finding_claim_validation(self) -> None:
        with pytest.raises(ValueError, match="claim"):
            Finding(
                finding_id="f-1",
                claim="",
                status=FindingState.SUPPORTED,
                supporting_evidence=(),
                contradicting_evidence=(),
                uncertainty="None.",
                evidence_basis=(),
            )


# ===================================================================
# INTEGRATION TESTS (S23 → S24 → S25)
# ===================================================================


class TestS23ToS25Integration:
    """S25 §32: Full pipeline Acquire → Evidence → Synthesize."""

    def setup_method(self) -> None:
        self.registry = ProviderRegistry()
        self.registry.register(StaticInformationProvider(), set_default=True)
        self.capability = ExternalInformationCapability(self.registry)
        self.service = EvidenceService()
        self.synthesizer = EvidenceSynthesizer(self.service)

    def test_full_pipeline_acquire_to_finding(self) -> None:
        # Step 1: Acquire through S23
        req1 = ExternalInformationRequest(
            query="NAV version", request_id="s25-req-001"
        )
        result1 = self.capability.acquire(req1)
        assert result1.is_success

        req2 = ExternalInformationRequest(
            query="NAV version info", request_id="s25-req-002"
        )
        result2 = self.capability.acquire(req2)
        assert result2.is_success

        # Step 2: Convert to S24 evidence
        ev_list1 = self.service.ingest_result(result1)
        ev_list2 = self.service.ingest_result(result2)
        assert self.service.evidence_count == 2

        # Step 3: Record S24 relation
        self.service.record_relation(
            ev_list1[0].evidence_id,
            ev_list2[0].evidence_id,
            RelationType.SUPPORTS,
            "Both confirm NAV v2.",
        )

        # Step 4: S25 synthesis
        finding = self.synthesizer.synthesize(
            [ev_list1[0].evidence_id, ev_list2[0].evidence_id],
            "NAV v2 is the current version.",
        )

        # Step 5: Verify finding
        assert finding.status == FindingState.SUPPORTED
        assert len(finding.evidence_basis) == 2
        assert finding.claim == "NAV v2 is the current version."

        # Step 6: Verify provenance chain
        for eid in finding.evidence_basis:
            trace = self.service.trace(eid)
            assert trace.source_name == "Static Knowledge Base"
            assert trace.provider_id == "static-provider-v1"

    def test_contested_finding_from_pipeline(self) -> None:
        """S25 §33: Conflict example through full pipeline."""
        # Create two evidence items with contradictory claims
        ev_a = _make_evidence("ev-date-a", "X occurred in 2020.", "Source A")
        ev_b = _make_evidence("ev-date-b", "X occurred in 2021.", "Source B")
        self.service._store.add_evidence(ev_a)
        self.service._store.add_evidence(ev_b)

        self.service.record_relation(
            "ev-date-a", "ev-date-b",
            RelationType.CONTRADICTS, "Different dates.",
        )

        finding = self.synthesizer.synthesize(
            ["ev-date-a", "ev-date-b"], "When did X occur?"
        )

        assert finding.status == FindingState.CONTESTED
        assert len(finding.supporting_evidence) == 0
        assert len(finding.contradicting_evidence) == 2
        assert "unresolved" in finding.uncertainty.lower()


# ===================================================================
# S24 PRESERVATION TESTS
# ===================================================================


class TestS24BehaviorPreserved:
    """S25 §37: Verify S24 behavior is not broken."""

    def test_s24_evidence_still_constructible(self) -> None:
        ev = _make_evidence("ev-preserve", "S24 still works.")
        assert ev.claim == "S24 still works."
        assert ev.evaluation_state == EvaluationState.UNASSESSED

    def test_s24_service_still_works(self) -> None:
        service = EvidenceService()
        ev = _make_evidence("ev-svc", "Service test.")
        service._store.add_evidence(ev)
        assert service.evidence_count == 1
        assert service.get_evidence("ev-svc") is not None

    def test_s24_evaluation_still_works(self) -> None:
        service = _setup_service_with_evidence([("ev-eval", "Eval test.")])
        evaluation = service.evaluate(
            "ev-eval", EvaluationState.SUPPORTED, "S25 did not break this."
        )
        assert evaluation.new_state == EvaluationState.SUPPORTED

    def test_s24_relations_still_work(self) -> None:
        service = _setup_service_with_evidence([
            ("ev-r1", "A."), ("ev-r2", "B."),
        ])
        rel = service.record_relation(
            "ev-r1", "ev-r2", RelationType.SUPPORTS
        )
        assert rel.relation_type == RelationType.SUPPORTS
        assert service.relation_count == 1

    def test_s24_trace_still_works(self) -> None:
        service = _setup_service_with_evidence([("ev-tr", "Trace.")])
        trace = service.trace("ev-tr")
        assert trace.evidence_id == "ev-tr"
        assert trace.source_name == "Test Source"


# ===================================================================
# S23 PRESERVATION TESTS
# ===================================================================


class TestS23BehaviorPreserved:
    """S25 §37: Verify S23 behavior is not broken."""

    def test_s23_static_provider_still_works(self) -> None:
        provider = StaticInformationProvider()
        req = ExternalInformationRequest(query="NAV version")
        result = provider.retrieve(req)
        assert result.status == RetrievalStatus.SUCCESS

    def test_s23_honesty_invariant_still_works(self) -> None:
        result = ExternalInformationResult(
            status=RetrievalStatus.PROVIDER_ERROR,
            items=[
                ExternalInformationItem(
                    content="Ghost.", source=_make_source()
                )
            ],
            provider_id="test",
        )
        with pytest.raises(ValueError, match="Integrity violation"):
            result.assert_honest()

