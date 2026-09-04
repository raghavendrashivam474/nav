"""S10 tests: Research cache TTL, hit/miss, provenance integrity."""

import time

from capabilities.research.cache import ResearchCache
from core.contracts.research import (
    ResearchQuery,
    SourceCandidate,
    SourceType,
)


def _make_query(q: str = "test query") -> ResearchQuery:
    return ResearchQuery(question=q)


def _make_candidates(n: int = 3) -> list[SourceCandidate]:
    return [
        SourceCandidate(
            url=f"https://example.com/{i}",
            title=f"Source {i}",
            snippet=f"Snippet {i}",
            source_type=SourceType.ARTICLE,
        )
        for i in range(n)
    ]


class TestResearchCache:
    def setup_method(self) -> None:
        self.cache = ResearchCache(max_size=10, default_ttl=60.0)

    def test_miss_on_empty(self) -> None:
        assert self.cache.get(_make_query()) is None
        assert self.cache.stats["misses"] == 1

    def test_put_and_get(self) -> None:
        q = _make_query()
        cands = _make_candidates()
        self.cache.put(q, cands)
        result = self.cache.get(q)
        assert result is not None
        assert len(result) == 3
        assert self.cache.stats["hits"] == 1

    def test_ttl_expiration(self) -> None:
        cache = ResearchCache(default_ttl=0.01)
        q = _make_query()
        cache.put(q, _make_candidates())
        time.sleep(0.02)
        assert cache.get(q) is None

    def test_normalization_is_deterministic(self) -> None:
        q1 = ResearchQuery(question="Solid State Batteries")
        q2 = ResearchQuery(question="batteries solid state")
        assert ResearchCache.normalize_query(q1) == ResearchCache.normalize_query(q2)

    def test_different_scope_different_key(self) -> None:
        q1 = ResearchQuery(question="batteries", scope="cost")
        q2 = ResearchQuery(question="batteries", scope="safety")
        assert ResearchCache.normalize_query(q1) != ResearchCache.normalize_query(q2)

    def test_max_size_eviction(self) -> None:
        cache = ResearchCache(max_size=2, default_ttl=60.0)
        for i in range(5):
            cache.put(_make_query(f"query {i}"), _make_candidates())
        assert cache.stats["size"] <= 2

    def test_clear_resets(self) -> None:
        self.cache.put(_make_query(), _make_candidates())
        self.cache.clear()
        assert self.cache.stats["size"] == 0
        assert self.cache.stats["hits"] == 0

    def test_cached_candidates_are_independent_copies(self) -> None:
        q = _make_query()
        cands = _make_candidates()
        self.cache.put(q, cands)
        result = self.cache.get(q)
        assert result is not None
        result.append(_make_candidates(1)[0])
        result2 = self.cache.get(q)
        assert result2 is not None
        assert len(result2) == 3
