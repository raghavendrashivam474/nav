"""S9 Live Search validation — requires network and duckduckgo-search.

Excluded from default test runs via the 'live' marker.
Run with: pytest -m live -v
"""

from __future__ import annotations

import pytest

from capabilities.research.providers.duckduckgo import DuckDuckGoSearchProvider
from core.contracts.research import ResearchQuery

pytestmark = pytest.mark.live


class TestLiveDuckDuckGoSearch:
    def test_real_search_returns_results(self):
        provider = DuckDuckGoSearchProvider()
        query = ResearchQuery(
            question="solid-state battery interface resistance",
            max_sources=5,
        )
        candidates = provider.discover(query)

        assert len(candidates) >= 1
        assert all(c.url.startswith("http") for c in candidates)
        assert all(len(c.title) > 0 for c in candidates)

    def test_real_search_respects_max_sources(self):
        provider = DuckDuckGoSearchProvider()
        query = ResearchQuery(
            question="machine learning retrieval augmented generation",
            max_sources=3,
        )
        candidates = provider.discover(query)

        assert len(candidates) <= 3
