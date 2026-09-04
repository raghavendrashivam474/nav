"""Brave Search provider - S10.

Implements SearchProvider protocol using the Brave Search API.
Requires BRAVE_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Any

from core.contracts.research import ResearchQuery, SourceCandidate, SourceType
from core.log import get_logger

logger = get_logger(__name__)


class BraveSearchProvider:
    """Brave Search API behind the SearchProvider protocol."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("BRAVE_API_KEY", "")
        self._base_url = "https://api.search.brave.com/res/v1/web/search"
        self.name = "brave"

    def discover(self, query: ResearchQuery) -> list[SourceCandidate]:
        if not self._api_key:
            logger.warning("BRAVE_API_KEY not configured, returning empty")
            return []

        try:
            import httpx

            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self._api_key,
            }
            params: dict[str, Any] = {
                "q": query.question,
                "count": min(query.max_sources, 20),
            }

            with httpx.Client(timeout=query.timeout_seconds) as client:
                resp = client.get(self._base_url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

            candidates: list[SourceCandidate] = []
            for item in data.get("web", {}).get("results", []):
                candidates.append(
                    SourceCandidate(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        snippet=item.get("description", ""),
                        source_type=SourceType.ARTICLE,
                    )
                )
            logger.info("Brave discovered %d candidates", len(candidates))
            return candidates

        except Exception as exc:
            logger.error("Brave search failed: %s", exc)
            return []
