"""S8 Progress tests — structured event emission at each research stage."""

from __future__ import annotations

from capabilities.research.discovery import MockSearchProvider
from capabilities.research.progress import (
    CollectingProgressReporter,
    NullProgressReporter,
    ProgressEvent,
    ProgressStage,
)
from capabilities.research.retrieval import MockRetriever
from capabilities.research.service import ResearchService
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.research import ResearchQuery


class FakeAIGateway(AIGateway):
    def generate(self, request: AIRequest) -> AIResponse:
        task = request.options.get("routing", {}).get("task_type", "")
        if task == "research_extraction":
            content = '[{"claim":"test claim","excerpt":"t","relevance":"high"}]'
        elif task == "research_synthesis":
            content = (
                '{"supported_findings":[{"statement":"s","evidence_ids":[],"notes":"n"}],'
                '"conflicting_evidence":[],'
                '"uncertainties":[],'
                '"open_questions":["q"]}'
            )
        else:
            content = "ok"
        return AIResponse(content=content, model_used="fake", usage={})


class TestProgressEvents:
    def test_all_stages_emitted(self):
        reporter = CollectingProgressReporter()
        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
            progress_reporter=reporter,
        )

        service.execute_research(
            ResearchQuery(question="solid-state battery")
        )

        stages = reporter.stages()
        assert ProgressStage.STARTED in stages
        assert ProgressStage.DISCOVERY in stages
        assert ProgressStage.RETRIEVAL in stages
        assert ProgressStage.EXTRACTION in stages
        assert ProgressStage.SYNTHESIS in stages
        assert ProgressStage.COMPLETED in stages

    def test_stage_ordering(self):
        reporter = CollectingProgressReporter()
        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
            progress_reporter=reporter,
        )

        service.execute_research(
            ResearchQuery(question="solid-state battery")
        )

        stages = reporter.stages()
        assert stages[0] == ProgressStage.STARTED
        assert stages[-1] == ProgressStage.COMPLETED

        discovery_idx = stages.index(ProgressStage.DISCOVERY)
        retrieval_idx = stages.index(ProgressStage.RETRIEVAL)
        extraction_idx = stages.index(ProgressStage.EXTRACTION)
        synthesis_idx = stages.index(ProgressStage.SYNTHESIS)

        assert discovery_idx < retrieval_idx
        assert retrieval_idx < extraction_idx
        assert extraction_idx < synthesis_idx

    def test_retrieval_progress_counts(self):
        reporter = CollectingProgressReporter()
        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
            progress_reporter=reporter,
        )

        service.execute_research(
            ResearchQuery(question="solid-state battery")
        )

        retrieval_events = [
            e for e in reporter.events if e.stage == ProgressStage.RETRIEVAL
        ]
        assert len(retrieval_events) >= 1

        final_retrieval = retrieval_events[-1]
        assert final_retrieval.total >= 1
        assert final_retrieval.completed <= final_retrieval.total

    def test_completed_event_metadata(self):
        reporter = CollectingProgressReporter()
        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
            progress_reporter=reporter,
        )

        service.execute_research(
            ResearchQuery(question="solid-state battery")
        )

        completed_events = [
            e for e in reporter.events if e.stage == ProgressStage.COMPLETED
        ]
        assert len(completed_events) == 1
        meta = completed_events[0].metadata
        assert "sources_retrieved" in meta
        assert "evidence_count" in meta

    def test_null_reporter_does_not_crash(self):
        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
            progress_reporter=NullProgressReporter(),
        )

        result = service.execute_research(
            ResearchQuery(question="solid-state battery")
        )
        assert result is not None

    def test_progress_event_serialization(self):
        event = ProgressEvent(
            stage=ProgressStage.RETRIEVAL,
            message="Test",
            completed=3,
            total=8,
        )
        d = event.to_dict()
        assert d["stage"] == "retrieval"
        assert d["completed"] == 3
        assert d["total"] == 8
        assert d["percent"] == 37.5
        assert "timestamp" in d

    def test_progress_event_percent_zero_total(self):
        event = ProgressEvent(
            stage=ProgressStage.STARTED, message="Starting"
        )
        assert event.percent == 0.0

    def test_failing_reporter_does_not_break_research(self):
        class BrokenReporter:
            def report(self, event: ProgressEvent) -> None:
                raise RuntimeError("Reporter exploded")

        service = ResearchService(
            gateway=FakeAIGateway(),
            search_provider=MockSearchProvider(),
            retriever=MockRetriever(),
            progress_reporter=BrokenReporter(),
        )

        result = service.execute_research(
            ResearchQuery(question="solid-state battery")
        )
        assert result is not None
