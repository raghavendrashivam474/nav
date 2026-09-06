"""
NAV v2 — S24: Evidence Layer Tests.

Covers:
- Evidence construction from S23 results
- Provenance preservation
- Evaluation state transitions
- Support/conflict relations
- Traceability back to S23 acquisition
- Integration: full S23 → S24 pipeline
- Integrity: failed retrieval cannot produce evidence
- S23 behavior preservation (no regressions)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from capabilities.evidence.evaluator import EvidenceEvaluator
from capabilities.evidence.factory import EvidenceFactory
from capabilities.evidence.relations import EvidenceRelationDetector
from capabilities.evidence.service import EvidenceService
from capabilities.evidence.store import EvidenceStore
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
    EvidenceRelation,
    EvidenceTrace,
    RelationType,
)
from core.contracts.external_information import (
    ExternalInformationItem,
    ExternalInformationRequest,
    ExternalInformationResult,
    RetrievalStatus,
    SourceMetadata,
)

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


def _make_success_result(
    items: list[ExternalInformationItem] | None = None,
    provider_id: str = "test-provider",
    request_id: str = "req-001",
) -> ExternalInformationResult:
    if items is None:
        items = [
            ExternalInformationItem(
                content="NAV v2 is the Personal Intelligence version.",
                source=_make_source(),
            )
        ]
    return ExternalInformationResult(
        status=RetrievalStatus.SUCCESS,
        items=items,
        provider_id=provider_id,
        request_id=request_id,
        completed_at=datetime(2025, 1, 15, 12, 0, 1, tzinfo=timezone.utc),
    )


def _make_failed_result(
    status: RetrievalStatus = RetrievalStatus.PROVIDER_ERROR,
) -> ExternalInformationResult:
    return ExternalInformationResult(
        status=status,
        items=[],
        provider_id="test-provider",
        request_id="req-fail",
        error_message="Something went wrong.",
    )


# ===================================================================
# EVIDENCE CONSTRUCTION TESTS
# ===================================================================


class TestEvidenceConstruction:
    """S24 §25: Evidence construction tests."""

    def test_valid_result_produces_evidence(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        assert len(evidence_list) == 1
        assert evidence_list[0].claim == "NAV v2 is the Personal Intelligence version."
        assert evidence_list[0].evaluation_state == EvaluationState.UNASSESSED

    def test_multiple_items_produce_multiple_evidence(self) -> None:
        items = [
            ExternalInformationItem(
                content="Claim A",
                source=_make_source(name="Source A"),
            ),
            ExternalInformationItem(
                content="Claim B",
                source=_make_source(name="Source B"),
            ),
        ]
        result = _make_success_result(items=items)
        evidence_list = EvidenceFactory.from_result(result)
        assert len(evidence_list) == 2
        assert evidence_list[0].item_index == 0
        assert evidence_list[1].item_index == 1
        assert evidence_list[0].claim == "Claim A"
        assert evidence_list[1].claim == "Claim B"

    def test_failed_retrieval_cannot_produce_evidence(self) -> None:
        """S24 §11: FAILED retrieval → NO valid evidence payload."""
        result = _make_failed_result()
        with pytest.raises(ValueError, match="non-successful"):
            EvidenceFactory.from_result(result)

    def test_no_results_cannot_produce_evidence(self) -> None:
        result = _make_failed_result(status=RetrievalStatus.NO_RESULTS)
        with pytest.raises(ValueError, match="non-successful"):
            EvidenceFactory.from_result(result)

    def test_timeout_cannot_produce_evidence(self) -> None:
        result = _make_failed_result(status=RetrievalStatus.TIMEOUT)
        with pytest.raises(ValueError, match="non-successful"):
            EvidenceFactory.from_result(result)

    def test_empty_claim_rejected(self) -> None:
        with pytest.raises(ValueError, match="claim must not be empty"):
            Evidence(
                evidence_id="ev-1",
                claim="",
                source_metadata=_make_source(),
                acquisition_provider_id="test",
            )

    def test_whitespace_claim_rejected(self) -> None:
        with pytest.raises(ValueError, match="claim must not be empty"):
            Evidence(
                evidence_id="ev-1",
                claim="   ",
                source_metadata=_make_source(),
                acquisition_provider_id="test",
            )

    def test_empty_evidence_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="evidence_id must not be empty"):
            Evidence(
                evidence_id="",
                claim="valid claim",
                source_metadata=_make_source(),
                acquisition_provider_id="test",
            )

    def test_negative_item_index_rejected(self) -> None:
        with pytest.raises(ValueError, match="item_index must be non-negative"):
            Evidence(
                evidence_id="ev-1",
                claim="valid claim",
                source_metadata=_make_source(),
                acquisition_provider_id="test",
                item_index=-1,
            )

    def test_evidence_is_frozen(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        with pytest.raises(AttributeError):
            evidence_list[0].claim = "modified"  # type: ignore[misc]


# ===================================================================
# PROVENANCE TESTS
# ===================================================================


class TestProvenance:
    """S24 §25: Provenance preservation tests."""

    def test_source_name_preserved(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        assert evidence_list[0].source_name == "Test Source"

    def test_source_url_preserved(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        assert evidence_list[0].source_url == "https://example.com"

    def test_query_preserved(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        assert evidence_list[0].source_metadata.query_echo == "test query"

    def test_acquisition_timestamp_preserved(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        assert evidence_list[0].acquisition_completed_at == datetime(
            2025, 1, 15, 12, 0, 1, tzinfo=timezone.utc
        )

    def test_provider_id_preserved(self) -> None:
        result = _make_success_result()
        evidence_list = EvidenceFactory.from_result(result)
        assert evidence_list[0].provider_id == "test-provider"
        assert evidence_list[0].acquisition_provider_id == "test-provider"

    def test_request_id_preserved(self) -> None:
        result = _make_success_result(request_id="req-xyz-789")
        evidence_list = EvidenceFactory.from_result(result)
        assert evidence_list[0].acquisition_request_id == "req-xyz-789"

    def test_source_metadata_is_direct_reference(self) -> None:
        """S24 §10: Evidence references S23 SourceMetadata, not a copy."""
        source = _make_source()
        item = ExternalInformationItem(content="test", source=source)
        result = _make_success_result(items=[item])
        evidence_list = EvidenceFactory.from_result(result)
        # The source_metadata should be the exact same object
        assert evidence_list[0].source_metadata is source


# ===================================================================
# EVALUATION TESTS
# ===================================================================


class TestEvaluation:
    """S24 §25: Evaluation tests."""

    def setup_method(self) -> None:
        self.evaluator = EvidenceEvaluator()
        self.evidence = Evidence(
            evidence_id="ev-eval-1",
            claim="Test claim for evaluation.",
            source_metadata=_make_source(),
            acquisition_provider_id="test",
        )

    def test_initial_state_is_unassessed(self) -> None:
        assert self.evidence.evaluation_state == EvaluationState.UNASSESSED

    def test_unassessed_to_supported(self) -> None:
        evaluation = self.evaluator.evaluate(
            self.evidence,
            EvaluationState.SUPPORTED,
            basis="Corroborated by independent source.",
        )
        assert evaluation.previous_state == EvaluationState.UNASSESSED
        assert evaluation.new_state == EvaluationState.SUPPORTED
        assert evaluation.basis == "Corroborated by independent source."

    def test_unassessed_to_contradicted(self) -> None:
        evaluation = self.evaluator.evaluate(
            self.evidence, EvaluationState.CONTRADICTED
        )
        assert evaluation.new_state == EvaluationState.CONTRADICTED

    def test_unassessed_to_conflicted(self) -> None:
        evaluation = self.evaluator.evaluate(
            self.evidence, EvaluationState.CONFLICTED
        )
        assert evaluation.new_state == EvaluationState.CONFLICTED

    def test_unassessed_to_uncertain(self) -> None:
        evaluation = self.evaluator.evaluate(
            self.evidence, EvaluationState.UNCERTAIN
        )
        assert evaluation.new_state == EvaluationState.UNCERTAIN

    def test_same_state_transition_rejected(self) -> None:
        with pytest.raises(ValueError, match="same state"):
            self.evaluator.evaluate(
                self.evidence, EvaluationState.UNASSESSED
            )

    def test_supported_to_contradicted(self) -> None:
        from dataclasses import replace

        supported = replace(
            self.evidence, evaluation_state=EvaluationState.SUPPORTED
        )
        evaluation = self.evaluator.evaluate(
            supported, EvaluationState.CONTRADICTED
        )
        assert evaluation.previous_state == EvaluationState.SUPPORTED
        assert evaluation.new_state == EvaluationState.CONTRADICTED

    def test_evaluation_is_deterministic(self) -> None:
        """Same inputs → same outputs (modulo timestamps)."""
        ev1 = self.evaluator.evaluate(
            self.evidence, EvaluationState.SUPPORTED, basis="test"
        )
        ev2 = self.evaluator.evaluate(
            self.evidence, EvaluationState.SUPPORTED, basis="test"
        )
        assert ev1.evidence_id == ev2.evidence_id
        assert ev1.previous_state == ev2.previous_state
        assert ev1.new_state == ev2.new_state
        assert ev1.basis == ev2.basis

    def test_evaluation_record_is_frozen(self) -> None:
        evaluation = self.evaluator.evaluate(
            self.evidence, EvaluationState.SUPPORTED
        )
        with pytest.raises(AttributeError):
            evaluation.new_state = EvaluationState.CONTRADICTED  # type: ignore[misc]


# ===================================================================
# RELATIONSHIP TESTS
# ===================================================================


class TestRelationships:
    """S24 §25: Relationship tests."""

    def test_support_relation(self) -> None:
        relation = EvidenceRelationDetector.record_relation(
            "ev-1", "ev-2", RelationType.SUPPORTS, "Same claim."
        )
        assert relation.relation_type == RelationType.SUPPORTS
        assert relation.source_evidence_id == "ev-1"
        assert relation.target_evidence_id == "ev-2"
        assert relation.basis == "Same claim."

    def test_contradiction_relation(self) -> None:
        relation = EvidenceRelationDetector.record_relation(
            "ev-1", "ev-2", RelationType.CONTRADICTS, "Different dates."
        )
        assert relation.relation_type == RelationType.CONTRADICTS

    def test_corroboration_relation(self) -> None:
        relation = EvidenceRelationDetector.record_relation(
            "ev-1", "ev-2", RelationType.CORROBORATES
        )
        assert relation.relation_type == RelationType.CORROBORATES

    def test_derived_from_relation(self) -> None:
        relation = EvidenceRelationDetector.record_relation(
            "ev-1", "ev-2", RelationType.DERIVED_FROM
        )
        assert relation.relation_type == RelationType.DERIVED_FROM

    def test_self_relation_rejected(self) -> None:
        with pytest.raises(ValueError, match="itself"):
            EvidenceRelation(
                relation_id="rel-1",
                source_evidence_id="ev-1",
                target_evidence_id="ev-1",
                relation_type=RelationType.SUPPORTS,
            )

    def test_empty_source_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="source_evidence_id"):
            EvidenceRelation(
                relation_id="rel-1",
                source_evidence_id="",
                target_evidence_id="ev-2",
                relation_type=RelationType.SUPPORTS,
            )

    def test_relation_is_frozen(self) -> None:
        relation = EvidenceRelationDetector.record_relation(
            "ev-1", "ev-2", RelationType.SUPPORTS
        )
        with pytest.raises(AttributeError):
            relation.relation_type = RelationType.CONTRADICTS  # type: ignore[misc]


# ===================================================================
# STORE TESTS
# ===================================================================


class TestEvidenceStore:
    """S24 §25: Store and traceability tests."""

    def setup_method(self) -> None:
        self.store = EvidenceStore()
        self.evidence = Evidence(
            evidence_id="ev-store-1",
            claim="Stored claim.",
            source_metadata=_make_source(),
            acquisition_provider_id="test",
        )

    def test_add_and_retrieve(self) -> None:
        self.store.add_evidence(self.evidence)
        retrieved = self.store.get_evidence("ev-store-1")
        assert retrieved is not None
        assert retrieved.claim == "Stored claim."

    def test_duplicate_add_rejected(self) -> None:
        self.store.add_evidence(self.evidence)
        with pytest.raises(ValueError, match="already exists"):
            self.store.add_evidence(self.evidence)

    def test_get_unknown_returns_none(self) -> None:
        assert self.store.get_evidence("nonexistent") is None

    def test_evidence_count(self) -> None:
        assert self.store.evidence_count == 0
        self.store.add_evidence(self.evidence)
        assert self.store.evidence_count == 1

    def test_trace_returns_full_provenance(self) -> None:
        self.store.add_evidence(self.evidence)
        trace = self.store.trace("ev-store-1")
        assert isinstance(trace, EvidenceTrace)
        assert trace.evidence_id == "ev-store-1"
        assert trace.claim == "Stored claim."
        assert trace.source_name == "Test Source"
        assert trace.source_url == "https://example.com"
        assert trace.provider_id == "test-provider"
        assert trace.original_query == "test query"
        assert trace.evaluation_state == EvaluationState.UNASSESSED

    def test_trace_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.store.trace("nonexistent")

    def test_add_relation_requires_existing_evidence(self) -> None:
        self.store.add_evidence(self.evidence)
        relation = EvidenceRelation(
            relation_id="rel-1",
            source_evidence_id="ev-store-1",
            target_evidence_id="ev-nonexistent",
            relation_type=RelationType.SUPPORTS,
        )
        with pytest.raises(ValueError, match="Target evidence not found"):
            self.store.add_relation(relation)

    def test_relations_queryable(self) -> None:
        ev2 = Evidence(
            evidence_id="ev-store-2",
            claim="Another claim.",
            source_metadata=_make_source(name="Source 2"),
            acquisition_provider_id="test",
        )
        self.store.add_evidence(self.evidence)
        self.store.add_evidence(ev2)
        relation = EvidenceRelation(
            relation_id="rel-1",
            source_evidence_id="ev-store-1",
            target_evidence_id="ev-store-2",
            relation_type=RelationType.CONTRADICTS,
        )
        self.store.add_relation(relation)
        rels = self.store.get_relations_for("ev-store-1")
        assert len(rels) == 1
        assert rels[0].relation_type == RelationType.CONTRADICTS


# ===================================================================
# INTEGRATION TESTS (S23 → S24)
# ===================================================================


class TestS23ToS24Integration:
    """S24 §25: End-to-end S23 acquisition → S24 evidence pipeline."""

    def setup_method(self) -> None:
        self.registry = ProviderRegistry()
        self.registry.register(StaticInformationProvider(), set_default=True)
        self.capability = ExternalInformationCapability(self.registry)
        self.service = EvidenceService()

    def test_full_pipeline_acquire_to_evidence(self) -> None:
        """S24 §32: Acquire → Convert → Preserve → Evaluate → Trace."""
        # Step 1: Acquire through S23
        req = ExternalInformationRequest(
            query="NAV version",
            request_id="integration-req-001",
        )
        result = self.capability.acquire(req)
        assert result.is_success

        # Step 2: Convert to evidence
        evidence_list = self.service.ingest_result(result)
        assert len(evidence_list) == 1

        ev = evidence_list[0]

        # Step 3: Provenance preserved
        assert "NAV v2" in ev.claim
        assert ev.source_name == "Static Knowledge Base"
        assert ev.provider_id == "static-provider-v1"
        assert ev.acquisition_request_id == "integration-req-001"
        assert ev.source_metadata.query_echo == "NAV version"

        # Step 4: Initial evaluation is UNASSESSED
        assert ev.evaluation_state == EvaluationState.UNASSESSED

        # Step 5: Evaluate
        evaluation = self.service.evaluate(
            ev.evidence_id,
            EvaluationState.SUPPORTED,
            basis="Static provider confirms NAV version.",
        )
        assert evaluation.new_state == EvaluationState.SUPPORTED

        # Step 6: Trace back to acquisition
        trace = self.service.trace(ev.evidence_id)
        assert trace.source_name == "Static Knowledge Base"
        assert trace.provider_id == "static-provider-v1"
        assert trace.original_query == "NAV version"
        assert trace.evaluation_state == EvaluationState.SUPPORTED

    def test_failed_acquisition_produces_no_evidence(self) -> None:
        """S24 §11: Failed retrieval must not silently become evidence."""
        req = ExternalInformationRequest(query="completely unknown topic xyz")
        result = self.capability.acquire(req)
        assert result.status == RetrievalStatus.NO_RESULTS

        with pytest.raises(ValueError, match="non-successful"):
            self.service.ingest_result(result)

    def test_multiple_acquisitions_with_relations(self) -> None:
        """S24 §14-15: Support and contradiction between evidence."""
        # Acquire two pieces of evidence
        req1 = ExternalInformationRequest(query="NAV version info")
        result1 = self.capability.acquire(req1)
        ev_list1 = self.service.ingest_result(result1)

        req2 = ExternalInformationRequest(query="S23 status check")
        result2 = self.capability.acquire(req2)
        ev_list2 = self.service.ingest_result(result2)

        assert self.service.evidence_count == 2

        # Record a support relation
        relation = self.service.record_relation(
            ev_list1[0].evidence_id,
            ev_list2[0].evidence_id,
            RelationType.SUPPORTS,
            basis="Both relate to NAV v2 development.",
        )
        assert relation.relation_type == RelationType.SUPPORTS
        assert self.service.relation_count == 1

        # Verify relations are queryable
        rels = self.service.get_relations_for(ev_list1[0].evidence_id)
        assert len(rels) == 1

    def test_evidence_count_after_ingestion(self) -> None:
        req = ExternalInformationRequest(query="NAV version")
        result = self.capability.acquire(req)
        self.service.ingest_result(result)
        assert self.service.evidence_count == 1
        assert len(self.service.get_all_evidence()) == 1

    def test_evaluation_history_tracked(self) -> None:
        req = ExternalInformationRequest(query="NAV version")
        result = self.capability.acquire(req)
        ev_list = self.service.ingest_result(result)
        ev_id = ev_list[0].evidence_id

        self.service.evaluate(ev_id, EvaluationState.SUPPORTED, "basis 1")
        self.service.evaluate(ev_id, EvaluationState.CONFLICTED, "basis 2")

        history = self.service.get_evaluation_history(ev_id)
        assert len(history) == 2
        assert history[0].new_state == EvaluationState.SUPPORTED
        assert history[1].new_state == EvaluationState.CONFLICTED


# ===================================================================
# S23 PRESERVATION TESTS
# ===================================================================


class TestS23BehaviorPreserved:
    """
    S24 §25: Verify S23 behavior is not broken by S24 additions.
    These tests re-validate key S23 invariants.
    """

    def test_s23_honesty_invariant_still_works(self) -> None:
        result = ExternalInformationResult(
            status=RetrievalStatus.PROVIDER_ERROR,
            items=[
                ExternalInformationItem(
                    content="Should not be here.",
                    source=_make_source(),
                )
            ],
            provider_id="test",
        )
        with pytest.raises(ValueError, match="Integrity violation"):
            result.assert_honest()

    def test_s23_static_provider_still_works(self) -> None:
        provider = StaticInformationProvider()
        req = ExternalInformationRequest(query="NAV version")
        result = provider.retrieve(req)
        assert result.status == RetrievalStatus.SUCCESS
        assert "NAV v2" in result.items[0].content

    def test_s23_capability_still_works(self) -> None:
        registry = ProviderRegistry()
        registry.register(StaticInformationProvider(), set_default=True)
        cap = ExternalInformationCapability(registry)
        req = ExternalInformationRequest(query="S23 status")
        result = cap.acquire(req)
        assert result.is_success
        assert result.has_items
