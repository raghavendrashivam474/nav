"""S8 Concurrency tests — bounded parallel retrieval, failure isolation, ordering."""

from __future__ import annotations

import threading
import time

from capabilities.research.concurrency import retrieve_concurrently
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.retrieval import MockRetriever
from capabilities.research.service import ResearchService
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.research import (
    ResearchQuery,
    ResearchSource,
    RetrievedContent,
    SourceRetriever,
    SourceStatus,
)


class ConcurrencyTrackingRetriever(SourceRetriever):
    """Retriever that tracks peak concurrent executions."""

    def __init__(self, delay: float = 0.05) -> None:
        self.name = "concurrency-tracker"
        self.delay = delay
        self._active = 0
        self._peak = 0
        self._lock = threading.Lock()

    @property
    def peak_concurrent(self) -> int:
        return self._peak

    def retrieve(self, source: ResearchSource, max_chars: int, timeout: float) -> RetrievedContent:
        with self._lock:
            self._active += 1
            self._peak = max(self._peak, self._active)
        time.sleep(self.delay)
        with self._lock:
            self._active -= 1
        return RetrievedContent(
            source_id=source.source_id,
            text=f"Content from {source.url}",
            content_type="text/plain",
        )


class FlakyRetriever(SourceRetriever):
    """Retriever that fails for specific URL patterns."""

    def __init__(self, fail_patterns: list[str]) -> None:
        self.name = "flaky"
        self._fail_patterns = fail_patterns

    def retrieve(self, source: ResearchSource, max_chars: int, timeout: float) -> RetrievedContent:
        for pattern in self._fail_patterns:
            if pattern in source.url:
                raise ConnectionError(f"Simulated failure for {pattern}")
        return RetrievedContent(
            source_id=source.source_id,
            text=f"Content from {source.url}",
        )


class SlowRetriever(SourceRetriever):
    """Retriever that simulates slow retrieval up to the timeout boundary."""

    def __init__(self, slow_patterns: list[str]) -> None:
        self.name = "slow"
        self._slow_patterns = slow_patterns

    def retrieve(self, source: ResearchSource, max_chars: int, timeout: float) -> RetrievedContent:
        for pattern in self._slow_patterns:
            if pattern in source.url:
                time.sleep(timeout + 0.05)
                raise TimeoutError("Simulated timeout")
        return RetrievedContent(
            source_id=source.source_id,
            text=f"Content from {source.url}",
        )


class FakeGateway(AIGateway):
    def generate(self, request: AIRequest) -> AIResponse:
        task = request.options.get("routing", {}).get("task_type", "")
        if task == "research_extraction":
            content = '[{"claim":"test","excerpt":"t","relevance":"high"}]'
        elif task == "research_synthesis":
            content = (
                '{"supported_findings":[],'
                '"conflicting_evidence":[],'
                '"uncertainties":[],'
                '"open_questions":[]}'
            )
        else:
            content = "ok"
        return AIResponse(content=content, model_used="fake", usage={})


class TestConcurrentRetrieval:
    def test_parallelism_proven(self):
        """Multiple sources should execute concurrently, not sequentially."""
        retriever = ConcurrencyTrackingRetriever(delay=0.05)
        sources = tuple(
            ResearchSource(
                source_id=f"s{i}",
                url=f"https://example.com/source{i}",
                canonical_url=f"https://example.com/source{i}",
                title=f"Source {i}",
            )
            for i in range(4)
        )

        outcomes = retrieve_concurrently(
            retriever=retriever,
            sources=sources,
            max_chars=1000,
            timeout=5.0,
            max_workers=4,
        )

        assert len(outcomes) == 4
        assert all(o.success for o in outcomes)
        assert retriever.peak_concurrent > 1, "Expected parallel execution but peak was 1"

    def test_concurrency_bounded(self):
        """No more than max_workers should execute simultaneously."""
        retriever = ConcurrencyTrackingRetriever(delay=0.05)
        sources = tuple(
            ResearchSource(
                source_id=f"s{i}",
                url=f"https://example.com/source{i}",
                canonical_url=f"https://example.com/source{i}",
                title=f"Source {i}",
            )
            for i in range(8)
        )

        retrieve_concurrently(
            retriever=retriever,
            sources=sources,
            max_chars=1000,
            timeout=5.0,
            max_workers=2,
        )

        assert retriever.peak_concurrent <= 2, (
            f"Exceeded max_workers: peak was {retriever.peak_concurrent}"
        )

    def test_failure_isolation(self):
        """One failed source must not cancel successful sources."""
        retriever = FlakyRetriever(fail_patterns=["source2"])
        sources = tuple(
            ResearchSource(
                source_id=f"s{i}",
                url=f"https://example.com/source{i}",
                canonical_url=f"https://example.com/source{i}",
                title=f"Source {i}",
            )
            for i in range(4)
        )

        outcomes = retrieve_concurrently(
            retriever=retriever,
            sources=sources,
            max_chars=1000,
            timeout=5.0,
        )

        successes = [o for o in outcomes if o.success]
        failures = [o for o in outcomes if not o.success]

        assert len(successes) == 3
        assert len(failures) == 1
        assert "source2" in failures[0].source.url

    def test_timeout_isolation(self):
        """A slow source must not hang the entire operation."""
        retriever = SlowRetriever(slow_patterns=["source1"])
        sources = tuple(
            ResearchSource(
                source_id=f"s{i}",
                url=f"https://example.com/source{i}",
                canonical_url=f"https://example.com/source{i}",
                title=f"Source {i}",
            )
            for i in range(3)
        )

        start = time.monotonic()
        outcomes = retrieve_concurrently(
            retriever=retriever,
            sources=sources,
            max_chars=1000,
            timeout=0.1,
        )
        elapsed = time.monotonic() - start

        successes = [o for o in outcomes if o.success]
        assert len(successes) >= 2
        assert elapsed < 1.0, f"Operation took too long: {elapsed:.1f}s"

    def test_empty_sources(self):
        """Zero sources should produce an empty result list."""
        retriever = MockRetriever()
        outcomes = retrieve_concurrently(
            retriever=retriever,
            sources=(),
            max_chars=1000,
            timeout=5.0,
        )
        assert outcomes == []

    def test_ordering_preserved(self):
        """Results must be in the same order as input sources."""
        retriever = ConcurrencyTrackingRetriever(delay=0.01)
        sources = tuple(
            ResearchSource(
                source_id=f"s{i}",
                url=f"https://example.com/source{i}",
                canonical_url=f"https://example.com/source{i}",
                title=f"Source {i}",
            )
            for i in range(5)
        )

        outcomes = retrieve_concurrently(
            retriever=retriever,
            sources=sources,
            max_chars=1000,
            timeout=5.0,
        )

        for i, outcome in enumerate(outcomes):
            assert outcome.source.source_id == f"s{i}"

    def test_service_integration_with_concurrency(self):
        """ResearchService should use concurrent retrieval end-to-end."""
        tracker = ConcurrencyTrackingRetriever(delay=0.03)
        service = ResearchService(
            gateway=FakeGateway(),
            search_provider=MockSearchProvider(),
            retriever=tracker,
            max_concurrent_retrievals=4,
        )

        result = service.execute_research(ResearchQuery(question="solid-state battery"))

        retrieved = result.sources_by_status(SourceStatus.RETRIEVED)
        assert len(retrieved) >= 2
        assert tracker.peak_concurrent > 1

    def test_max_sources_limit_preserved(self):
        """Concurrency must not bypass the max_sources limit."""
        retriever = MockRetriever()
        service = ResearchService(
            search_provider=MockSearchProvider(),
            retriever=retriever,
            max_concurrent_retrievals=4,
        )

        result = service.execute_research(
            ResearchQuery(question="solid-state battery", max_sources=2)
        )

        assert len(result.sources) <= 2
