"""Bounded concurrent retrieval for Research — S8.

Parallelizes independent source retrieval using a bounded thread pool.
Preserves S7 partial-failure semantics: one failed source never cancels
successful independent sources.

Invariant 7: Research concurrency is bounded.
Invariant 8: One failed source cannot invalidate successful independent sources.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from core.contracts.research import (
    ResearchSource,
    RetrievedContent,
    SourceRetriever,
)
from core.log import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_WORKERS = 4


@dataclass(frozen=True)
class RetrievalOutcome:
    """Result of a single source retrieval attempt."""

    source: ResearchSource
    content: RetrievedContent | None
    error: str | None
    duration_seconds: float

    @property
    def success(self) -> bool:
        return self.content is not None and self.error is None


def _retrieve_one(
    retriever: SourceRetriever,
    source: ResearchSource,
    max_chars: int,
    timeout: float,
) -> RetrievalOutcome:
    """Execute a single retrieval with full error isolation."""
    start = time.monotonic()
    try:
        content = retriever.retrieve(
            source=source, max_chars=max_chars, timeout=timeout
        )
        duration = time.monotonic() - start
        logger.debug("Retrieved %s in %.2fs", source.url, duration)
        return RetrievalOutcome(
            source=source,
            content=content,
            error=None,
            duration_seconds=duration,
        )
    except TimeoutError as exc:
        duration = time.monotonic() - start
        logger.warning("Timeout retrieving %s: %s", source.url, exc)
        return RetrievalOutcome(
            source=source,
            content=None,
            error="Timeout",
            duration_seconds=duration,
        )
    except Exception as exc:
        duration = time.monotonic() - start
        logger.warning("Failed retrieving %s: %s", source.url, exc)
        return RetrievalOutcome(
            source=source,
            content=None,
            error=str(exc),
            duration_seconds=duration,
        )


def retrieve_concurrently(
    retriever: SourceRetriever,
    sources: tuple[ResearchSource, ...],
    max_chars: int,
    timeout: float,
    max_workers: int = DEFAULT_MAX_WORKERS,
    on_source_complete: Callable[[int, int, str], None] | None = None,
) -> list[RetrievalOutcome]:
    """Retrieve multiple sources concurrently with bounded parallelism."""
    if not sources:
        return []

    effective_workers = min(max_workers, len(sources))
    total = len(sources)
    completed = 0

    logger.info(
        "Starting concurrent retrieval: %d sources, max_workers=%d",
        total,
        effective_workers,
    )

    outcomes_map: dict[str, RetrievalOutcome] = {}

    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        future_to_source = {
            executor.submit(
                _retrieve_one, retriever, source, max_chars, timeout
            ): source
            for source in sources
        }

        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                outcome = future.result()
            except Exception as exc:
                outcome = RetrievalOutcome(
                    source=source,
                    content=None,
                    error=f"Unexpected executor error: {exc}",
                    duration_seconds=0.0,
                )
            outcomes_map[source.source_id] = outcome
            completed += 1

            if on_source_complete is not None:
                on_source_complete(completed, total, source.url)

    ordered = [outcomes_map[s.source_id] for s in sources]

    success_count = sum(1 for o in ordered if o.success)
    logger.info(
        "Concurrent retrieval complete: %d/%d successful", success_count, total
    )

    return ordered
