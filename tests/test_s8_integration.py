"""S8 Integration tests — end-to-end capability cooperation."""

from __future__ import annotations

from pathlib import Path

from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from capabilities.research.capability import ResearchCapability
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.progress import (
    CollectingProgressReporter,
    ProgressStage,
)
from capabilities.research.retrieval import MockRetriever
from capabilities.research.service import ResearchService
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.capability import Request
from core.contracts.memory import MemoryQuery
from core.contracts.research import ResearchQuery
from core.orchestration.orchestrator import Orchestrator


class FakeAIGateway(AIGateway):
    def __init__(self) -> None:
        self.calls: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResponse:
        self.calls.append(request)
        task = request.options.get("routing", {}).get("task_type", "")
        if task == "research_extraction":
            content = (
                '[{"claim":"Interface resistance is high",'
                '"excerpt":"gaps form","relevance":"high"}]'
            )
        elif task == "research_synthesis":
            content = (
                '{"supported_findings":[{"statement":"Resistance is the bottleneck",'
                '"evidence_ids":["ev_1"],"notes":"confirmed"}],'
                '"conflicting_evidence":[],'
                '"uncertainties":[],'
                '"open_questions":["Scaling?"]}'
            )
        else:
            content = "ok"
        return AIResponse(content=content, model_used="fake", usage={})


class TestOrchestratorResearchIntegration:
    def test_orchestrator_routes_research_with_progress(self):
        registry = CapabilityRegistry()
        reporter = CollectingProgressReporter()
        gateway = FakeAIGateway()
        cap = ResearchCapability(gateway=gateway, progress_reporter=reporter)
        registry.register(cap)

        orchestrator = Orchestrator(registry)
        req = Request(
            request_id="req_s8_1",
            payload={"question": "Research solid-state batteries"},
        )

        resp = orchestrator.route_request("research", req)

        assert resp.success is True
        assert "findings" in resp.data
        assert "sources" in resp.data
        assert len(reporter.events) > 0
        assert ProgressStage.COMPLETED in reporter.stages()

    def test_research_uses_ai_gateway(self):
        gateway = FakeAIGateway()
        service = ResearchService(
            gateway=gateway,
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
        )

        service.execute_research(ResearchQuery(question="solid-state battery"))

        assert len(gateway.calls) >= 2
        task_types = [c.options.get("routing", {}).get("task_type", "") for c in gateway.calls]
        assert "research_extraction" in task_types
        assert "research_synthesis" in task_types

    def test_research_memory_optional_persistence(self, tmp_path: Path):
        repo = SQLiteMemoryRepository(db_path=tmp_path / "s8_mem.db")
        mem = MemoryService(repository=repo)
        gateway = FakeAIGateway()

        cap = ResearchCapability(gateway=gateway, memory=mem)
        req = Request(
            request_id="req_s8_2",
            payload={
                "question": "Research solid-state batteries",
                "save_to_memory": True,
            },
        )

        resp = cap.invoke(req)
        assert resp.success is True

        memories = mem.retrieve(MemoryQuery(tags=["research"]))
        assert len(memories) >= 1

    def test_research_without_memory_still_works(self):
        gateway = FakeAIGateway()
        cap = ResearchCapability(gateway=gateway, memory=None)
        req = Request(
            request_id="req_s8_3",
            payload={
                "question": "Research solid-state batteries",
                "save_to_memory": True,
            },
        )

        resp = cap.invoke(req)
        assert resp.success is True

    def test_simple_cognition_not_affected(self):
        """Simple requests should not go through research pipeline."""
        from capabilities.cognition.cognition import CognitionCapability

        registry = CapabilityRegistry()
        registry.register(CognitionCapability())
        registry.register(ResearchCapability())

        orchestrator = Orchestrator(registry)
        req = Request(
            request_id="req_s8_simple",
            payload={"prompt": "What is 2+2?"},
        )

        resp = orchestrator.route_request("cognition", req)
        assert resp.request_id == "req_s8_simple"

    def test_capability_version_bumped(self):
        cap = ResearchCapability()
        assert cap.version == "0.1.0"

    def test_partial_failures_visible_in_response(self):
        class FlakyRetriever(MockRetriever):
            def retrieve(self, source, max_chars, timeout):
                if "sulfide" in source.url:
                    raise ConnectionError("Simulated failure")
                return super().retrieve(source, max_chars, timeout)

        gateway = FakeAIGateway()
        cap = ResearchCapability(
            gateway=gateway,
            search_provider=MockSearchProvider(),
            retriever=FlakyRetriever(),
        )

        req = Request(
            request_id="req_s8_4",
            payload={"question": "Research solid-state batteries"},
        )
        resp = cap.invoke(req)
        assert resp.success is True

        sources = resp.data["sources"]
        statuses = [s["status"] for s in sources]
        assert "retrieved" in statuses
        assert "failed" in statuses
