"""Policy-driven model router for the S5 Hybrid AI Layer.

The router selects an AI provider by:
  1. Removing providers that violate hard constraints.
  2. Ranking remaining providers by soft preferences.
  3. Returning the best match with a fallback chain.

All decisions are deterministic and logged.
"""

from __future__ import annotations

from ai.errors import RoutingError
from ai.routing.types import (
    CostClass,
    Locality,
    ProviderMetadata,
    QualityClass,
    RoutingContext,
    RoutingDecision,
)
from core.log import get_logger

logger = get_logger(__name__)


class ModelRouter:
    """Selects the best available AI provider for a given routing context."""

    def __init__(self, registry: dict[str, ProviderMetadata]) -> None:
        self._registry = registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(self, context: RoutingContext) -> RoutingDecision:
        """Determine which provider should handle this request."""
        candidates = self._apply_constraints(context)

        if not candidates:
            raise RoutingError(
                "No compatible provider available after applying constraints. "
                f"privacy={context.privacy}, constraints={context.constraints}"
            )

        ranked = self._rank_by_preferences(context, candidates)
        selected_name = ranked[0][0]
        fallback_chain = tuple(name for name, _ in ranked[1:])
        reason = self._explain(context, selected_name)

        logger.info(
            "Routing decision: provider=%s, reason=%s, fallbacks=%s",
            selected_name,
            reason,
            list(fallback_chain) if fallback_chain else "none",
        )

        return RoutingDecision(
            provider_name=selected_name,
            reason=reason,
            fallback_chain=fallback_chain,
        )

    # ------------------------------------------------------------------
    # Constraint filtering (hard rules — violations are forbidden)
    # ------------------------------------------------------------------

    def _apply_constraints(self, ctx: RoutingContext) -> list[tuple[str, ProviderMetadata]]:
        """Remove providers that violate any hard constraint."""
        candidates: list[tuple[str, ProviderMetadata]] = []

        for name, meta in self._registry.items():
            if not meta.available:
                logger.debug("Excluding %s: marked unavailable", name)
                continue

            # Hard constraint: local_only privacy
            if ctx.privacy == "local_only" and meta.locality != Locality.LOCAL:
                logger.debug("Excluding %s: violates local_only privacy", name)
                continue

            # Hard constraint: explicit constraint list
            if "local_only" in ctx.constraints and meta.locality != Locality.LOCAL:
                logger.debug("Excluding %s: violates local_only constraint", name)
                continue

            if "no_paid" in ctx.constraints and meta.cost_class == CostClass.PAID:
                logger.debug("Excluding %s: violates no_paid constraint", name)
                continue

            candidates.append((name, meta))

        return candidates

    # ------------------------------------------------------------------
    # Preference ranking (soft optimization)
    # ------------------------------------------------------------------

    def _rank_by_preferences(
        self,
        ctx: RoutingContext,
        candidates: list[tuple[str, ProviderMetadata]],
    ) -> list[tuple[str, ProviderMetadata]]:
        """Score and sort candidates by how well they match preferences."""

        def _score(item: tuple[str, ProviderMetadata]) -> int:
            _, meta = item
            score = 0

            # Quality preference
            if ctx.quality_requirement == "high" and meta.quality_class == QualityClass.HIGH:
                score += 10

            # Cost preference
            if ctx.cost_preference == "low" and meta.cost_class == CostClass.FREE:
                score += 8

            # Locality preference
            if ctx.privacy == "local_only" or "local_preferred" in ctx.preferences:
                if meta.locality == Locality.LOCAL:
                    score += 5

            # Simplicity preference
            if ctx.complexity == "simple" and meta.locality == Locality.LOCAL:
                score += 3

            # Latency preference
            if ctx.latency_preference == "low" and meta.latency_class == "low":
                score += 2

            return score

        return sorted(candidates, key=_score, reverse=True)

    # ------------------------------------------------------------------
    # Explanation (for logging / observability)
    # ------------------------------------------------------------------

    @staticmethod
    def _explain(ctx: RoutingContext, provider_name: str) -> str:
        parts: list[str] = []
        if ctx.privacy == "local_only":
            parts.append("privacy=local_only")
        if ctx.quality_requirement == "high":
            parts.append("quality=high")
        if ctx.cost_preference == "low":
            parts.append("cost=low")
        if ctx.complexity == "simple":
            parts.append("complexity=simple")
        if not parts:
            parts.append("default")
        parts.append(f"selected={provider_name}")
        return " + ".join(parts)
