"""S10 tests: Search router primary/fallback behavior."""

from capabilities.research.providers.router import SearchRouter
from core.contracts.research import (
    ResearchQuery,
    SourceCandidate,
    SourceType,
)


class FakeProvider:
    def __init__(
        self,
        name: str,
        results: list[SourceCandidate] | None = None,
        should_fail: bool = False,
    ) -> None:
        self.name = name
        self._results = results or []
        self._should_fail = should_fail

    def discover(self, query: ResearchQuery) -> list[SourceCandidate]:
        if self._should_fail:
            raise ConnectionError(f"{self.name} failed")
        return self._results


def _candidate(url: str = "https://example.com") -> SourceCandidate:
    return SourceCandidate(url=url, title="Test", snippet="Test", source_type=SourceType.ARTICLE)


class TestSearchRouter:
    def test_primary_success(self) -> None:
        primary = FakeProvider("p", [_candidate()])
        router = SearchRouter(primary=primary)  # type: ignore[arg-type]
        results = router.discover(ResearchQuery(question="test"))
        assert len(results) == 1

    def test_fallback_on_primary_failure(self) -> None:
        primary = FakeProvider("p", should_fail=True)
        fallback = FakeProvider("f", [_candidate("https://fallback.com")])
        router = SearchRouter(primary=primary, fallback=fallback)  # type: ignore[arg-type]
        results = router.discover(ResearchQuery(question="test"))
        assert len(results) == 1
        assert results[0].url == "https://fallback.com"

    def test_fallback_on_empty_primary(self) -> None:
        primary = FakeProvider("p", [])
        fallback = FakeProvider("f", [_candidate()])
        router = SearchRouter(primary=primary, fallback=fallback)  # type: ignore[arg-type]
        results = router.discover(ResearchQuery(question="test"))
        assert len(results) == 1

    def test_both_fail_returns_empty(self) -> None:
        primary = FakeProvider("p", should_fail=True)
        fallback = FakeProvider("f", should_fail=True)
        router = SearchRouter(primary=primary, fallback=fallback)  # type: ignore[arg-type]
        results = router.discover(ResearchQuery(question="test"))
        assert results == []

    def test_no_fallback_returns_empty(self) -> None:
        primary = FakeProvider("p", should_fail=True)
        router = SearchRouter(primary=primary)  # type: ignore[arg-type]
        results = router.discover(ResearchQuery(question="test"))
        assert results == []

    def test_name_includes_providers(self) -> None:
        primary = FakeProvider("ddg")
        fallback = FakeProvider("brave")
        router = SearchRouter(primary=primary, fallback=fallback)  # type: ignore[arg-type]
        assert "ddg" in router.name
        assert "brave" in router.name
