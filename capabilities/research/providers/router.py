"""Search router - S10.

Routes search requests through primary and fallback providers.
Implements the SearchProvider protocol so ResearchService sees
a single unified provider.
"""

from __future__ import annotations

from core.contracts.research import ResearchQuery, SearchProvider, SourceCandidate
from core.log import get_logger

logger = get_logger(__name__)


class SearchRouter:
    """Primary/fallback search routing behind the SearchProvider protocol."""

    def __init__(
        self,
        primary: SearchProvider,
        fallback: SearchProvider | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self.name = self._build_name()

    def _build_name(self) -> str:
        p_name = getattr(self._primary, "name", "unknown")
        if self._fallback:
            f_name = getattr(self._fallback, "name", "unknown")
            return f"router({p_name}+{f_name})"
        return f"router({p_name})"

    def discover(self, query: ResearchQuery) -> list[SourceCandidate]:
        try:
            results = self._primary.discover(query)
            if results:
                return results
            logger.warning(
                "Primary provider '%s' returned empty results",
                getattr(self._primary, "name", "unknown"),
            )
        except Exception as exc:
            logger.warning(
                "Primary provider '%s' failed: %s",
                getattr(self._primary, "name", "unknown"),
                exc,
            )

        if self._fallback is not None:
            logger.info(
                "Falling back to '%s'",
                getattr(self._fallback, "name", "unknown"),
            )
            try:
                return self._fallback.discover(query)
            except Exception as exc:
                logger.error(
                    "Fallback provider '%s' also failed: %s",
                    getattr(self._fallback, "name", "unknown"),
                    exc,
                )

        return []
