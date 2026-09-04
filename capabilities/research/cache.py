"""Research cache - S10.

TTL-based cache for search discovery results (SourceCandidates).
Caches raw search hits, NOT synthesized answers, to preserve
freshness and provenance integrity.
"""

from __future__ import annotations

import threading
import time

from core.contracts.research import ResearchQuery, SourceCandidate
from core.log import get_logger

logger = get_logger(__name__)


class ResearchCache:
    """Thread-safe TTL cache for search discovery results."""

    def __init__(self, max_size: int = 200, default_ttl: float = 300.0) -> None:
        self._cache: dict[str, tuple[list[SourceCandidate], float]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

    @staticmethod
    def normalize_query(query: ResearchQuery) -> str:
        """Deterministic cache key from query parameters."""
        terms = sorted(query.question.lower().split())
        scope = (query.scope or "").lower().strip()
        return f"{' '.join(terms)}|{scope}|{query.depth}"

    def get(self, query: ResearchQuery) -> list[SourceCandidate] | None:
        """Return cached candidates if valid, else None."""
        key = self.normalize_query(query)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            candidates, expires_at = entry
            if time.monotonic() > expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            logger.debug("Cache hit for query: %s", query.question[:50])
            return list(candidates)

    def put(
        self,
        query: ResearchQuery,
        candidates: list[SourceCandidate],
        ttl: float | None = None,
    ) -> None:
        """Cache discovery results with TTL."""
        key = self.normalize_query(query)
        effective_ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            if len(self._cache) >= self._max_size:
                self._evict_oldest()
            self._cache[key] = (
                list(candidates),
                time.monotonic() + effective_ttl,
            )

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._cache),
            }

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
        del self._cache[oldest_key]
