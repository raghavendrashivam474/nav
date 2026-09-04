"""S9 Search Provider tests — deterministic, no live network.

Validates DuckDuckGoSearchProvider using mocked DDGS client.
All tests run offline and must pass in CI.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from capabilities.research.providers.duckduckgo import DuckDuckGoSearchProvider
from core.contracts.research import (
    ResearchQuery,
    SearchProvider,
    SourceType,
)


class TestProtocolConformance:
    def test_satisfies_search_provider_protocol(self) -> None:
        """DuckDuckGoSearchProvider must satisfy the SearchProvider Protocol."""
        provider = DuckDuckGoSearchProvider()
        assert hasattr(provider, "name")
        assert isinstance(provider.name, str)
        assert hasattr(provider, "discover")
        assert callable(provider.discover)

    def test_can_be_used_as_search_provider_type(self) -> None:
        """Verify it can be passed where SearchProvider is expected."""
        provider: SearchProvider = DuckDuckGoSearchProvider()
        assert provider.name == "duckduckgo"


class TestDuckDuckGoDiscovery:
    def _make_mock_ddgs(self, results: list[dict]) -> MagicMock:
        """Create a mock DDGS context manager returning canned results."""
        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = iter(results)
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)
        return mock_ddgs

    def test_discover_returns_candidates(self) -> None:
        """Valid DDGS results become SourceCandidates."""
        mock_instance = self._make_mock_ddgs(
            [
                {
                    "href": "https://example.com/article",
                    "title": "Test Article",
                    "body": "This is a test snippet.",
                },
                {
                    "href": "https://arxiv.org/abs/1234",
                    "title": "A Paper on ArXiv",
                    "body": "Abstract text here.",
                },
            ]
        )

        with patch("ddgs.DDGS", return_value=mock_instance):
            provider = DuckDuckGoSearchProvider()
            query = ResearchQuery(question="test query", max_sources=5)
            candidates = provider.discover(query)

            assert len(candidates) == 2
            assert candidates[0].url == "https://example.com/article"
            assert candidates[0].title == "Test Article"
            assert candidates[0].snippet == "This is a test snippet."
            assert candidates[1].source_type == SourceType.PAPER

    def test_discover_respects_max_sources(self) -> None:
        """Provider should not return more than query.max_sources."""
        mock_instance = self._make_mock_ddgs(
            [
                {"href": f"https://example.com/{i}", "title": f"Result {i}", "body": ""}
                for i in range(20)
            ]
        )

        with patch("ddgs.DDGS", return_value=mock_instance):
            provider = DuckDuckGoSearchProvider()
            query = ResearchQuery(question="test", max_sources=3)
            candidates = provider.discover(query)

            assert len(candidates) == 3

    def test_discover_handles_empty_results(self) -> None:
        """Empty DDGS results produce empty candidate list."""
        mock_instance = self._make_mock_ddgs([])

        with patch("ddgs.DDGS", return_value=mock_instance):
            provider = DuckDuckGoSearchProvider()
            candidates = provider.discover(ResearchQuery(question="xyzzy"))

            assert candidates == []

    def test_discover_handles_network_failure(self) -> None:
        """Network errors produce empty list, not exceptions."""
        mock_instance = MagicMock()
        mock_instance.text.side_effect = ConnectionError("Network down")
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)

        with patch("ddgs.DDGS", return_value=mock_instance):
            provider = DuckDuckGoSearchProvider()
            candidates = provider.discover(ResearchQuery(question="test"))

            assert candidates == []

    def test_discover_skips_results_without_url(self) -> None:
        """Results missing href or title are filtered out."""
        mock_instance = self._make_mock_ddgs(
            [
                {"href": "", "title": "No URL", "body": "skip"},
                {"href": "https://good.com", "title": "", "body": "skip"},
                {"href": "https://valid.com", "title": "Valid", "body": "keep"},
            ]
        )

        with patch("ddgs.DDGS", return_value=mock_instance):
            provider = DuckDuckGoSearchProvider()
            candidates = provider.discover(ResearchQuery(question="test"))

            assert len(candidates) == 1
            assert candidates[0].url == "https://valid.com"


class TestSourceTypeInference:
    def test_infers_paper_from_arxiv(self) -> None:
        url = "https://arxiv.org/abs/123"
        assert DuckDuckGoSearchProvider._infer_type(url) == SourceType.PAPER

    def test_infers_paper_from_pdf(self) -> None:
        url = "https://example.com/report.pdf"
        assert DuckDuckGoSearchProvider._infer_type(url) == SourceType.PAPER

    def test_infers_documentation_from_github(self) -> None:
        url = "https://github.com/user/repo"
        assert DuckDuckGoSearchProvider._infer_type(url) == SourceType.DOCUMENTATION

    def test_infers_official_from_gov(self) -> None:
        url = "https://nist.gov/standard"
        assert DuckDuckGoSearchProvider._infer_type(url) == SourceType.OFFICIAL_SITE

    def test_defaults_to_article(self) -> None:
        url = "https://blog.example.com/post"
        assert DuckDuckGoSearchProvider._infer_type(url) == SourceType.ARTICLE


class TestServiceIntegration:
    def test_default_provider_is_mock(self, monkeypatch) -> None:
        monkeypatch.delenv("NAV_SEARCH_PROVIDER", raising=False)
        from capabilities.research.service import ResearchService

        service = ResearchService()
        assert service.search_provider.name == "mock-search"

    def test_env_selects_duckduckgo(self, monkeypatch) -> None:
        monkeypatch.setenv("NAV_SEARCH_PROVIDER", "duckduckgo")
        from capabilities.research.service import ResearchService

        service = ResearchService()
        assert service.search_provider.name == "duckduckgo"

    def test_unknown_provider_falls_back_to_mock(self, monkeypatch) -> None:
        monkeypatch.setenv("NAV_SEARCH_PROVIDER", "nonexistent")
        from capabilities.research.service import ResearchService

        service = ResearchService()
        assert service.search_provider.name == "mock-search"
