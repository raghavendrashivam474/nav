"""Comprehensive unit and integration test suite for S7 Research Capability."""

from __future__ import annotations

from pathlib import Path

from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from capabilities.research.capability import ResearchCapability
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.extraction import EvidenceExtractor
from capabilities.research.provenance import ProvenanceTracker
from capabilities.research.retrieval import MockRetriever, normalize_url
from capabilities.research.service import ResearchService
from capabilities.research.synthesis import EvidenceSynthesizer
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.capability import Request
from core.contracts.memory import MemoryQuery
from core.contracts.research import (
    ResearchEvidence,
    ResearchQuery,
    ResearchResult,
    ResearchSource,
    SourceCandidate,
    SourceStatus,
    SourceType,
    SupportState,
)
from core.orchestration.orchestrator import Orchestrator

# ---------------------------------------------------------------------------
# Test AI Gateway (Offline / Deterministic Fake)
# ---------------------------------------------------------------------------


class FakeAIGateway(AIGateway):
    """Deterministic AIGateway for tests returning pre-canned or structured AI responses."""

    def __init__(self) -> None:
        self.calls: list[AIRequest] = []
        self.custom_response: str | None = None
        self.should_fail: bool = False

    def generate(self, request: AIRequest) -> AIResponse:
        self.calls.append(request)
        if self.should_fail:
            raise RuntimeError("Gateway forced error")

        if self.custom_response is not None:
            return AIResponse(
                content=self.custom_response,
                model_used="fake-model",
                usage={"tokens": 100},
            )

        task_type = request.options.get("routing", {}).get("task_type", "")
        if task_type == "research_extraction":
            content = """[
                {
                    "claim": "Solid-state electrolyte interfaces suffer high impedance.",
                    "excerpt": "microscopic gaps form at the interface",
                    "relevance": "high"
                },
                {
                    "claim": "Sulfide electrolytes have higher conductivity than oxides.",
                    "excerpt": "exceeding 10-2 S/cm",
                    "relevance": "medium"
                }
            ]"""
        elif task_type == "research_synthesis":
            content = """{
                "supported_findings": [
                    {
                        "statement": "Interface resistance remains a primary bottleneck.",
                        "evidence_ids": ["ev_1", "ev_2"],
                        "notes": "Supported across multiple literature sources."
                    }
                ],
                "conflicting_evidence": [
                    {
                        "statement": "Oxide vs sulfide commercial viability trade-offs.",
                        "evidence_ids": ["ev_3", "ev_4"],
                        "notes": "Sulfides have high conductivity but poor ambient stability."
                    }
                ],
                "uncertainties": [
                    {
                        "statement": "Polymer interlayers may prevent dendrite growth.",
                        "evidence_ids": ["ev_5"],
                        "notes": "Experimental stage, lacks industrial validation."
                    }
                ],
                "open_questions": [
                    "Can dry-room calendering roll-to-roll machinery scale to gigafactories?"
                ]
            }"""
        else:
            content = "Fake AI generated response."

        return AIResponse(
            content=content,
            model_used="fake-model",
            usage={"tokens": 100},
        )


# ---------------------------------------------------------------------------
# Contract Tests
# ---------------------------------------------------------------------------


class TestResearchContracts:
    def test_query_creation_defaults(self):
        query = ResearchQuery(question="Test question")
        assert query.question == "Test question"
        assert query.max_sources == 8
        assert query.depth == "standard"
        assert query.timeout_seconds == 15.0

    def test_source_creation(self):
        source = ResearchSource(
            source_id="src_1",
            url="https://example.com/paper",
            canonical_url="https://example.com/paper",
            title="A Paper",
            source_type=SourceType.PAPER,
            status=SourceStatus.RETRIEVED,
        )
        assert source.source_id == "src_1"
        assert source.status == SourceStatus.RETRIEVED
        assert source.source_type == SourceType.PAPER

    def test_evidence_creation(self):
        ev = ResearchEvidence(
            evidence_id="ev_1",
            source_id="src_1",
            claim="Interface resistance is high",
            excerpt="Measured resistance exceeds 500 ohms",
            relevance="high",
        )
        assert ev.source_id == "src_1"
        assert ev.claim == "Interface resistance is high"

    def test_result_helper_methods(self):
        s1 = ResearchSource(
            source_id="s1",
            url="https://a.com",
            canonical_url="https://a.com",
            title="A",
            status=SourceStatus.RETRIEVED,
        )
        s2 = ResearchSource(
            source_id="s2",
            url="https://b.com",
            canonical_url="https://b.com",
            title="B",
            status=SourceStatus.FAILED,
        )
        e1 = ResearchEvidence(evidence_id="e1", source_id="s1", claim="Claim 1")
        e2 = ResearchEvidence(evidence_id="e2", source_id="s1", claim="Claim 2")

        result = ResearchResult(
            query=ResearchQuery(question="Test"),
            sources=(s1, s2),
            evidence=(e1, e2),
        )

        assert len(result.sources_by_status(SourceStatus.RETRIEVED)) == 1
        assert len(result.sources_by_status(SourceStatus.FAILED)) == 1
        assert len(result.evidence_for("s1")) == 2
        assert len(result.evidence_for("s2")) == 0


# ---------------------------------------------------------------------------
# URL Normalization & Deduplication Tests
# ---------------------------------------------------------------------------


class TestUrlNormalization:
    def test_trailing_slash_normalization(self):
        assert normalize_url("https://example.com/article/") == "https://example.com/article"
        assert normalize_url("https://example.com/article") == "https://example.com/article"

    def test_case_normalization(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Article") == "https://example.com/Article"

    def test_default_port_stripping(self):
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_utm_parameter_stripping(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&key=val"
        normalized = normalize_url(url)
        assert "utm_source" not in normalized
        assert "key=val" in normalized

    def test_provenance_deduplication(self):
        query = ResearchQuery(question="Test")
        tracker = ProvenanceTracker(query)

        c1 = SourceCandidate(url="https://example.com/paper/", title="Paper")
        c2 = SourceCandidate(url="https://example.com/paper", title="Paper Duplicate")

        s1 = tracker.register_candidate(c1)
        s2 = tracker.register_candidate(c2)

        # Must map to the exact same source record
        assert s1.source_id == s2.source_id
        assert len(tracker.get_sources()) == 1


# ---------------------------------------------------------------------------
# Retrieval & Partial Failure Tests
# ---------------------------------------------------------------------------


class TestRetrieval:
    def test_mock_retriever_content(self):
        retriever = MockRetriever()
        source = ResearchSource(
            source_id="s1",
            url="https://battery-institute.org/solid-state-intro",
            canonical_url="https://battery-institute.org/solid-state-intro",
            title="Intro",
        )
        content = retriever.retrieve(source, max_chars=1000, timeout=5.0)
        assert "Solid-state battery interfaces" in content.text
        assert content.truncated is False

    def test_content_truncation(self):
        retriever = MockRetriever()
        source = ResearchSource(
            source_id="s1",
            url="https://battery-institute.org/solid-state-intro",
            canonical_url="https://battery-institute.org/solid-state-intro",
            title="Intro",
        )
        content = retriever.retrieve(source, max_chars=50, timeout=5.0)
        assert len(content.text) == 50
        assert content.truncated is True

    def test_partial_failure_handling_in_service(self):
        """If one source fails (raises exception), others succeed and workflow continues."""

        class FlakyRetriever(MockRetriever):
            def retrieve(self, source: ResearchSource, max_chars: int, timeout: float):
                if "sulfide" in source.url:
                    raise ConnectionResetError("Connection dropped")
                return super().retrieve(source, max_chars, timeout)

        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=FlakyRetriever(),
        )

        result = service.execute_research(ResearchQuery(question="solid-state battery"))
        retrieved = result.sources_by_status(SourceStatus.RETRIEVED)
        failed = result.sources_by_status(SourceStatus.FAILED)

        assert len(retrieved) > 0
        assert len(failed) == 1
        assert "Connection dropped" in str(failed[0].error)


# ---------------------------------------------------------------------------
# Extraction & Synthesis Parser Tests
# ---------------------------------------------------------------------------


class TestExtractionAndSynthesis:
    def test_extractor_handles_markdown_wrapped_json(self):
        gateway = FakeAIGateway()
        gateway.custom_response = """```json
        [
            {
                "claim": "Lithium dendrites short circuit cells",
                "excerpt": "dendrites short circuit",
                "relevance": "high"
            }
        ]
        ```"""
        extractor = EvidenceExtractor(gateway)
        content = MockRetriever().retrieve(
            ResearchSource(
                source_id="s1",
                url="https://test.com",
                canonical_url="https://test.com",
                title="Test",
            ),
            max_chars=1000,
            timeout=5.0,
        )

        ev_list = extractor.extract(ResearchQuery(question="dendrites"), content)
        assert len(ev_list) == 1
        assert ev_list[0].claim == "Lithium dendrites short circuit cells"
        assert ev_list[0].source_id == "s1"

    def test_extractor_fallback_on_bad_ai_output(self):
        gateway = FakeAIGateway()
        gateway.custom_response = (
            "Here are some notes:\n- First claim found.\n- Second claim found."
        )
        extractor = EvidenceExtractor(gateway)
        content = MockRetriever().retrieve(
            ResearchSource(
                source_id="s1",
                url="https://test.com",
                canonical_url="https://test.com",
                title="Test",
            ),
            max_chars=1000,
            timeout=5.0,
        )

        ev_list = extractor.extract(ResearchQuery(question="notes"), content)
        assert len(ev_list) == 2
        assert "First claim found" in ev_list[0].claim

    def test_synthesizer_builds_provenance_map(self):
        gateway = FakeAIGateway()
        synthesizer = EvidenceSynthesizer(gateway)

        s = ResearchSource(
            source_id="s1",
            url="https://test.com",
            canonical_url="https://test.com",
            title="Test",
        )
        e1 = ResearchEvidence(evidence_id="ev_1", source_id="s1", claim="Bottleneck exists")
        e2 = ResearchEvidence(evidence_id="ev_2", source_id="s1", claim="Resistance is high")

        result = synthesizer.synthesize(
            ResearchQuery(question="bottlenecks"),
            sources=(s,),
            evidence=(e1, e2),
        )

        assert len(result.findings) >= 1
        assert result.findings[0].support == SupportState.SUPPORTED
        assert "ev_1" in result.findings[0].evidence_ids
        assert len(result.conflicts) >= 1
        assert len(result.uncertainties) >= 1
        assert len(result.open_questions) >= 1


# ---------------------------------------------------------------------------
# End-to-End Capability & Orchestration Tests
# ---------------------------------------------------------------------------


class TestResearchCapabilityIntegration:
    def test_capability_metadata(self):
        cap = ResearchCapability()
        assert cap.name == "research"
        assert cap.version == "0.1.0"
        assert "research map" in cap.description.lower()

    def test_orchestrator_routes_to_research(self):
        registry = CapabilityRegistry()
        gateway = FakeAIGateway()
        cap = ResearchCapability(gateway=gateway)
        registry.register(cap)

        orchestrator = Orchestrator(registry)
        req = Request(
            request_id="req_r1",
            payload={"question": "Research solid-state batteries and technical challenges."},
        )

        resp = orchestrator.route_request("research", req)
        assert resp.success is True
        assert "findings" in resp.data
        assert "sources" in resp.data
        assert len(resp.data["sources"]) > 0

    def test_capability_persists_to_memory_when_requested(self, tmp_path: Path):
        repo = SQLiteMemoryRepository(db_path=tmp_path / "research_mem.db")
        mem_service = MemoryService(repository=repo)
        gateway = FakeAIGateway()

        cap = ResearchCapability(gateway=gateway, memory=mem_service)

        req = Request(
            request_id="req_r2",
            payload={
                "question": "Research solid-state batteries",
                "save_to_memory": True,
            },
        )

        resp = cap.invoke(req)
        assert resp.success is True

        # Check memory store for saved research finding
        memories = mem_service.retrieve(MemoryQuery(tags=["research"]))
        assert len(memories) >= 1
        assert "Interface resistance" in memories[0].value
        assert memories[0].metadata["type"] == "research_finding"

    def test_missing_question_returns_graceful_error(self):
        cap = ResearchCapability()
        req = Request(request_id="req_r3", payload={})
        resp = cap.invoke(req)
        assert resp.success is False
        assert resp.error is not None
        assert "Missing required field" in resp.error
