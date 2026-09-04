"""DuckDuckGo search provider for NAV Research — S9 P0.

Implements the SearchProvider Protocol using ddgs.
Zero API keys required. Suitable for real-world validation
and developer-local testing.

Rate limits are soft and IP-based. The provider handles failures
gracefully by returning an empty candidate list, allowing the
research pipeline's existing partial-failure semantics to apply.
"""

from __future__ import annotations

from core.contracts.research import (
    ResearchQuery,
    SourceCandidate,
    SourceType,
)
from core.log import get_logger

logger = get_logger(__name__)


class DuckDuckGoSearchProvider:
    """Live web search via DuckDuckGo.

    Satisfies the SearchProvider Protocol:
      - name: str
      - discover(query: ResearchQuery) -> list[SourceCandidate]
    """

    def __init__(self, name: str = "duckduckgo") -> None:
        self.name = name

    def discover(self, query: ResearchQuery) -> list[SourceCandidate]:
        """Query DuckDuckGo and return structured source candidates.

        Failures are logged and result in an empty list rather than
        crashing the research pipeline. This preserves S7/S8 partial-
        failure semantics.
        """
        logger.info(
            "DuckDuckGo search: '%s' (max_sources=%d)",
            query.question,
            query.max_sources,
        )

        try:
            from ddgs import DDGS
        except ImportError:
            logger.error(
                "ddgs package not installed. "
                "Run: pip install ddgs"
            )
            return []

        candidates: list[SourceCandidate] = []

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query.question,
                    max_results=query.max_sources,
                ))

                for result in results:
                    href = result.get("href", "").strip()
                    title = result.get("title", "").strip()
                    body = result.get("body", "").strip()

                    if not href or not title:
                        continue

                    candidates.append(
                        SourceCandidate(
                            url=href,
                            title=title,
                            snippet=body,
                            source_type=self._infer_type(href),
                            publisher=None,
                        )
                    )

            logger.info(
                "DuckDuckGo returned %d candidate(s)", len(candidates)
            )

        except Exception as exc:
            logger.error("DuckDuckGo search failed: %s", exc)

        return candidates[: query.max_sources]

    @staticmethod
    def _infer_type(url: str) -> SourceType:
        """Best-effort source type inference from URL patterns."""
        lower = url.lower()
        if any(d in lower for d in [".pdf", "arxiv.org", "scholar.google"]):
            return SourceType.PAPER
        if any(d in lower for d in ["github.com", "docs.", "readthedocs"]):
            return SourceType.DOCUMENTATION
        if any(d in lower for d in [".gov", ".edu", "who.int"]):
            return SourceType.OFFICIAL_SITE
        if "patent" in lower:
            return SourceType.PATENT
        return SourceType.ARTICLE
