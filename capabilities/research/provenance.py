"""Provenance layer — S7.

Tracks sources, performs deterministic deduplication using normalized URLs,
and builds the evidence-to-source traceability matrix.
"""

from __future__ import annotations

import uuid

from capabilities.research.retrieval import normalize_url
from core.contracts.research import (
    ResearchQuery,
    ResearchSource,
    SourceCandidate,
    SourceStatus,
    utcnow,
)


class ProvenanceTracker:
    """Manages sources and ensures strict ID-to-source traceability."""

    def __init__(self, query: ResearchQuery) -> None:
        self.query = query
        self._sources: dict[str, ResearchSource] = {}
        # Map normalized URLs to source_ids to prevent duplicates
        self._url_map: dict[str, str] = {}

    def register_candidate(self, candidate: SourceCandidate) -> ResearchSource:
        """Register a discovered candidate. Deduplicates by normalized URL."""
        norm_url = normalize_url(candidate.url)

        if norm_url in self._url_map:
            # Already tracked, return existing record
            source_id = self._url_map[norm_url]
            return self._sources[source_id]

        # Allocate brand-new stable ID
        source_id = f"src_{uuid.uuid4().hex[:8]}"
        source = ResearchSource(
            source_id=source_id,
            url=candidate.url,
            canonical_url=norm_url,
            title=candidate.title,
            source_type=candidate.source_type,
            publisher=candidate.publisher,
            status=SourceStatus.DISCOVERED,
        )

        self._sources[source_id] = source
        self._url_map[norm_url] = source_id
        return source

    def update_status(
        self,
        source_id: str,
        status: SourceStatus,
        error: str | None = None,
        metadata_update: dict | None = None,
    ) -> ResearchSource:
        """Transition a source to retrieved, failed, or skipped."""
        if source_id not in self._sources:
            raise KeyError(f"Source ID {source_id} is not registered")

        orig = self._sources[source_id]
        meta = {**orig.metadata, **(metadata_update or {})}

        updated = ResearchSource(
            source_id=orig.source_id,
            url=orig.url,
            canonical_url=orig.canonical_url,
            title=orig.title,
            source_type=orig.source_type,
            publisher=orig.publisher,
            status=status,
            retrieved_at=utcnow() if status == SourceStatus.RETRIEVED else orig.retrieved_at,
            error=error,
            metadata=meta,
        )
        self._sources[source_id] = updated
        return updated

    def get_sources(self) -> tuple[ResearchSource, ...]:
        return tuple(self._sources.values())

    def get_source(self, source_id: str) -> ResearchSource:
        return self._sources[source_id]
