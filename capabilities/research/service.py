"""Research Service — S7 + S8.

Orchestrates the research lifecycle:
  1. Discovery of source candidates
  2. Deterministic registration and deduplication via ProvenanceTracker
  3. Bounded concurrent retrieval with partial failure isolation (S8)
  4. AI-assisted evidence extraction
  5. AI-assisted synthesis with uncertainty and contradiction mapping

S8 additions:
  - Concurrent retrieval via ThreadPoolExecutor (bounded)
  - Structured progress reporting (decoupled from interfaces)
  - All S7 limits, timeouts, and failure semantics preserved
"""

from __future__ import annotations

from capabilities.research.concurrency import (
    DEFAULT_MAX_WORKERS,
    RetrievalOutcome,
    retrieve_concurrently,
)
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.extraction import EvidenceExtractor
from capabilities.research.progress import (
    NullProgressReporter,
    ProgressEvent,
    ProgressReporter,
    ProgressStage,
)
from capabilities.research.provenance import ProvenanceTracker
from capabilities.research.retrieval import MockRetriever
from capabilities.research.synthesis import EvidenceSynthesizer
from core.contracts.ai import AIGateway
from core.contracts.research import (
    ResearchEvidence,
    ResearchQuery,
    ResearchResult,
    RetrievedContent,
    SearchProvider,
    SourceRetriever,
    SourceStatus,
)
from core.log import get_logger

logger = get_logger(__name__)


class ResearchService:
    """Core workflow engine for systematic investigation."""

    def __init__(
        self,
        gateway: AIGateway | None = None,
        search_provider: SearchProvider | None = None,
        retriever: SourceRetriever | None = None,
        progress_reporter: ProgressReporter | None = None,
        max_concurrent_retrievals: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        self.search_provider = search_provider or MockSearchProvider()
        self.retriever = retriever or MockRetriever()
        self.gateway = gateway
        self.progress_reporter = progress_reporter or NullProgressReporter()
        self.max_concurrent_retrievals = max(1, max_concurrent_retrievals)

        self.extractor: EvidenceExtractor | None = None
        self.synthesizer: EvidenceSynthesizer | None = None

        if gateway is not None:
            self.extractor = EvidenceExtractor(gateway)
            self.synthesizer = EvidenceSynthesizer(gateway)

    def _emit(
        self,
        stage: ProgressStage,
        message: str,
        completed: int = 0,
        total: int = 0,
        **metadata: object,
    ) -> None:
        """Emit a progress event to the attached reporter."""
        try:
            self.progress_reporter.report(
                ProgressEvent(
                    stage=stage,
                    message=message,
                    completed=completed,
                    total=total,
                    metadata={k: v for k, v in metadata.items()},
                )
            )
        except Exception as exc:
            logger.warning("Progress reporting failed (non-fatal): %s", exc)

    def execute_research(self, query: ResearchQuery) -> ResearchResult:
        """Executes the full end-to-end bounded research workflow."""
        logger.info("Starting research on query: '%s'", query.question)
        self._emit(ProgressStage.STARTED, f"Research started: {query.question}")
        tracker = ProvenanceTracker(query)

        # -------------------------------------------------------------
        # 1. Source Discovery
        # -------------------------------------------------------------
        try:
            candidates = self.search_provider.discover(query)
            logger.info("Discovered %d candidate source(s)", len(candidates))
        except Exception as exc:
            logger.error("Search discovery failed: %s", exc)
            candidates = []

        self._emit(
            ProgressStage.DISCOVERY,
            f"Discovered {len(candidates)} source(s)",
            completed=len(candidates),
            total=len(candidates),
        )

        # -------------------------------------------------------------
        # 2. Registration & Deduplication
        # -------------------------------------------------------------
        for candidate in candidates[: query.max_sources]:
            tracker.register_candidate(candidate)

        registered_sources = tracker.get_sources()

        # -------------------------------------------------------------
        # 3. Bounded Concurrent Retrieval (S8)
        # -------------------------------------------------------------
        self._emit(
            ProgressStage.RETRIEVAL,
            f"Retrieving {len(registered_sources)} source(s)",
            completed=0,
            total=len(registered_sources),
        )

        def _on_source_complete(
            completed: int, total: int, url: str
        ) -> None:
            self._emit(
                ProgressStage.RETRIEVAL,
                f"Retrieved {completed}/{total} sources",
                completed=completed,
                total=total,
                source_url=url,
            )

        outcomes: list[RetrievalOutcome] = retrieve_concurrently(
            retriever=self.retriever,
            sources=registered_sources,
            max_chars=query.max_content_chars,
            timeout=query.timeout_seconds,
            max_workers=self.max_concurrent_retrievals,
            on_source_complete=_on_source_complete,
        )

        # Update tracker sequentially (thread-safe) from outcomes
        retrieved_contents: list[RetrievedContent] = []
        for outcome in outcomes:
            if outcome.success and outcome.content is not None:
                tracker.update_status(
                    outcome.source.source_id, SourceStatus.RETRIEVED
                )
                retrieved_contents.append(outcome.content)
            else:
                tracker.update_status(
                    outcome.source.source_id,
                    SourceStatus.FAILED,
                    error=outcome.error,
                )

        # -------------------------------------------------------------
        # 4. AI-assisted Evidence Extraction
        # -------------------------------------------------------------
        self._emit(
            ProgressStage.EXTRACTION,
            f"Extracting evidence from {len(retrieved_contents)} source(s)",
            completed=0,
            total=len(retrieved_contents),
        )

        all_evidence: list[ResearchEvidence] = []

        for idx, content in enumerate(retrieved_contents, 1):
            if self.extractor is not None:
                extracted = self.extractor.extract(query, content)
            else:
                extracted = EvidenceExtractor._fallback_extraction(
                    content.source_id, content.text, query.question
                )
            all_evidence.extend(extracted)
            self._emit(
                ProgressStage.EXTRACTION,
                f"Extracted evidence from {idx}/{len(retrieved_contents)}",
                completed=idx,
                total=len(retrieved_contents),
            )

        logger.info("Total extracted evidence points: %d", len(all_evidence))

        # -------------------------------------------------------------
        # 5. AI-assisted Synthesis
        # -------------------------------------------------------------
        self._emit(ProgressStage.SYNTHESIS, "Synthesizing findings")

        final_sources = tracker.get_sources()
        evidence_tuple = tuple(all_evidence)

        if self.synthesizer is not None:
            result = self.synthesizer.synthesize(
                query=query,
                sources=final_sources,
                evidence=evidence_tuple,
            )
        else:
            result = EvidenceSynthesizer._fallback_synthesis(
                query=query,
                sources=final_sources,
                evidence=evidence_tuple,
            )

        self._emit(
            ProgressStage.COMPLETED,
            "Research complete",
            completed=1,
            total=1,
            sources_retrieved=len(retrieved_contents),
            sources_failed=len(final_sources) - len(retrieved_contents),
            evidence_count=len(all_evidence),
        )

        return result
