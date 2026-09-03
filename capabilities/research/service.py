"""Research Service — S7.

Orchestrates the research lifecycle:
  1. Discovery of source candidates
  2. Deterministic registration and deduplication via ProvenanceTracker
  3. Bounded retrieval with partial failure isolation
  4. AI-assisted evidence extraction
  5. AI-assisted synthesis with uncertainty and contradiction mapping
"""

from __future__ import annotations

from capabilities.research.discovery import MockSearchProvider
from capabilities.research.extraction import EvidenceExtractor
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
    ) -> None:
        self.search_provider = search_provider or MockSearchProvider()
        self.retriever = retriever or MockRetriever()
        self.gateway = gateway

        self.extractor: EvidenceExtractor | None = None
        self.synthesizer: EvidenceSynthesizer | None = None

        if gateway is not None:
            self.extractor = EvidenceExtractor(gateway)
            self.synthesizer = EvidenceSynthesizer(gateway)

    def execute_research(self, query: ResearchQuery) -> ResearchResult:
        """Executes the full end-to-end bounded research workflow."""
        logger.info("Starting research on query: '%s'", query.question)
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

        # -------------------------------------------------------------
        # 2. Registration & Deduplication
        # -------------------------------------------------------------
        for candidate in candidates[: query.max_sources]:
            tracker.register_candidate(candidate)

        registered_sources = tracker.get_sources()

        # -------------------------------------------------------------
        # 3. Bounded Retrieval with Partial Failure Isolation
        # -------------------------------------------------------------
        retrieved_contents: list[RetrievedContent] = []

        for source in registered_sources:
            try:
                content = self.retriever.retrieve(
                    source=source,
                    max_chars=query.max_content_chars,
                    timeout=query.timeout_seconds,
                )
                tracker.update_status(source.source_id, SourceStatus.RETRIEVED)
                retrieved_contents.append(content)
                logger.debug("Successfully retrieved source: %s", source.url)
            except TimeoutError as exc:
                logger.warning("Timeout retrieving %s: %s", source.url, exc)
                tracker.update_status(source.source_id, SourceStatus.FAILED, error="Timeout")
            except Exception as exc:
                logger.warning("Failed retrieving %s: %s", source.url, exc)
                tracker.update_status(source.source_id, SourceStatus.FAILED, error=str(exc))

        # -------------------------------------------------------------
        # 4. AI-assisted Evidence Extraction
        # -------------------------------------------------------------
        all_evidence: list[ResearchEvidence] = []

        for content in retrieved_contents:
            if self.extractor is not None:
                extracted = self.extractor.extract(query, content)
            else:
                # Deterministic fallback extraction when gateway is absent
                extracted = EvidenceExtractor._fallback_extraction(
                    content.source_id, content.text, query.question
                )
            all_evidence.extend(extracted)

        logger.info("Total extracted evidence points: %d", len(all_evidence))

        # -------------------------------------------------------------
        # 5. AI-assisted Synthesis
        # -------------------------------------------------------------
        final_sources = tracker.get_sources()
        evidence_tuple = tuple(all_evidence)

        if self.synthesizer is not None:
            result = self.synthesizer.synthesize(
                query=query,
                sources=final_sources,
                evidence=evidence_tuple,
            )
        else:
            # Deterministic fallback synthesis when gateway is absent
            result = EvidenceSynthesizer._fallback_synthesis(
                query=query,
                sources=final_sources,
                evidence=evidence_tuple,
            )

        return result
