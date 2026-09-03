"""Discovery layer — S7.

Provides search and discovery capability.  Includes a flexible
MockSearchProvider designed for offline tests and off-grid live demos.
"""

from __future__ import annotations

import urllib.parse

from core.contracts.research import (
    ResearchQuery,
    SearchProvider,
    SourceCandidate,
    SourceType,
)


class MockSearchProvider(SearchProvider):
    """Offline-first search provider that returns pre-loaded candidates or
    generates structured technical candidates based on query terms."""

    def __init__(self, name: str = "mock-search") -> None:
        self.name = name
        self._preset_candidates: list[SourceCandidate] = []

    def add_candidate(self, candidate: SourceCandidate) -> None:
        """Register a specific search result for testing."""
        self._preset_candidates.append(candidate)

    def discover(self, query: ResearchQuery) -> list[SourceCandidate]:
        if self._preset_candidates:
            return self._preset_candidates[: query.max_sources]

        # Dynamic generators for off-grid demos/fallback tests
        q = query.question.lower()
        candidates: list[SourceCandidate] = []

        if "solid-state" in q or "battery" in q or "batteries" in q:
            candidates = [
                SourceCandidate(
                    url="https://battery-institute.org/solid-state-intro",
                    title="Introduction to Solid-State Battery Interfaces",
                    snippet=(
                        "Analysis of interface impedance and chemical stability "
                        "in solid-state cells."
                    ),
                    source_type=SourceType.ARTICLE,
                    publisher="Battery Institute",
                ),
                SourceCandidate(
                    url="https://academic-materials.org/papers/sulfide-vs-oxide-electrolyte",
                    title="Sulfide vs Oxide Electrolytes for Solid-State Batteries",
                    snippet=(
                        "Comparative study of ion conductivity and mechanical challenges "
                        "in sulfides vs oxides."
                    ),
                    source_type=SourceType.PAPER,
                    publisher="Materials Journal",
                ),
                SourceCandidate(
                    url="https://industry-tech-news.com/battery-manufacturing-scale",
                    title="Manufacturing Challenges at Scale for Solid Batteries",
                    snippet=(
                        "Explores roll-to-roll compatibility and dry-room requirements "
                        "for solid state assembly."
                    ),
                    source_type=SourceType.REPORT,
                    publisher="Industry Tech News",
                ),
                SourceCandidate(
                    url="https://patent-office.gov/patents/us1102934-dendrite-prevention",
                    title="US Patent 1102934: Lithium Metal Dendrite Suppression Layer",
                    snippet=(
                        "A novel structured polymer interlayer designed to mitigate "
                        "dendritic growth at high current densities."
                    ),
                    source_type=SourceType.PATENT,
                    publisher="US Patent Office",
                ),
            ]
        else:
            # Fallback generic candidate
            safe_query = urllib.parse.quote_plus(query.question[:50])
            candidates = [
                SourceCandidate(
                    url=f"https://encyclopedia-tech.org/wiki/{safe_query}",
                    title=f"General Overview: {query.question}",
                    snippet=(
                        f"Information, definitions, and active research directions "
                        f"regarding: '{query.question}'."
                    ),
                    source_type=SourceType.ARTICLE,
                    publisher="Tech Encyclopedia",
                )
            ]

        return candidates[: query.max_sources]
