"""Default AIGateway implementation with S5 Model Router integration.

Delegates to AI providers selected by the policy-driven ModelRouter.
NAV Core and capabilities remain fully decoupled from the active provider.

The gateway:
  1. Registers all available providers at init time.
  2. Extracts routing hints from AIRequest.options["routing"].
  3. Asks the ModelRouter to select the best provider.
  4. Executes the request with automatic fallback.
  5. Never violates hard constraints (e.g., local_only privacy).
"""

from __future__ import annotations

import os

from ai.errors import ConfigurationError, ProviderError, RoutingError
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.openai_provider import OpenAIProvider
from ai.routing.router import ModelRouter
from ai.routing.types import (
    CostClass,
    Locality,
    ProviderMetadata,
    QualityClass,
    RoutingContext,
    RoutingDecision,
)
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.log import get_logger

logger = get_logger(__name__)


class DefaultAIGateway(AIGateway):
    """Concrete AIGateway backed by the S5 ModelRouter.

    Backward compatible: if no routing hints are provided, behaviour
    matches S3 (uses NAV_AI_PROVIDER or defaults to ollama).
    """

    def __init__(self) -> None:
        self._providers: dict[str, OllamaProvider | OpenAIProvider] = {}
        self._metadata: dict[str, ProviderMetadata] = {}

        self._init_providers()
        self._router = ModelRouter(self._metadata)

        logger.info(
            "DefaultAIGateway initialized with %d provider(s): %s",
            len(self._providers),
            list(self._providers.keys()),
        )

    # ------------------------------------------------------------------
    # Provider registration
    # ------------------------------------------------------------------

    def _init_providers(self) -> None:
        """Discover and register all available AI providers."""
        preferred = os.environ.get("NAV_AI_PROVIDER", "ollama").lower()

        # --- Ollama (local, free) ---
        ollama_url = os.environ.get(
            "NAV_OLLAMA_URL", "http://localhost:11434/api/chat"
        )
        ollama_model = os.environ.get("NAV_OLLAMA_MODEL", "mistral")
        self._providers["ollama"] = OllamaProvider(
            base_url=ollama_url, model=ollama_model
        )
        self._metadata["ollama"] = ProviderMetadata(
            name="ollama",
            locality=Locality.LOCAL,
            cost_class=CostClass.FREE,
            quality_class=QualityClass.STANDARD,
        )
        logger.info("Registered provider: ollama (model=%s)", ollama_model)

        # --- OpenAI (remote, paid) ---
        api_key = os.environ.get("NAV_OPENAI_API_KEY", "")
        if api_key and api_key.strip():
            openai_model = os.environ.get("NAV_OPENAI_MODEL", "gpt-4o-mini")
            self._providers["openai"] = OpenAIProvider(
                api_key=api_key, model=openai_model
            )
            self._metadata["openai"] = ProviderMetadata(
                name="openai",
                locality=Locality.REMOTE,
                cost_class=CostClass.PAID,
                quality_class=QualityClass.HIGH,
            )
            logger.info("Registered provider: openai (model=%s)", openai_model)
        elif preferred == "openai":
            # Preserve S3 behaviour: explicit openai without key is an error
            raise ConfigurationError(
                "NAV_OPENAI_API_KEY is not set but 'openai' provider was selected."
            )

        if not self._providers:
            raise ConfigurationError("No AI providers could be initialized.")

    # ------------------------------------------------------------------
    # AIGateway contract
    # ------------------------------------------------------------------

    def generate(self, request: AIRequest) -> AIResponse:
        """Route request through the best compatible provider."""
        context = self._build_routing_context(request)

        try:
            decision = self._router.route(context)
        except RoutingError:
            # If the router finds no candidates, attempt legacy fallback
            decision = self._legacy_fallback()
            logger.warning(
                "Router found no candidates; using legacy fallback -> %s",
                decision.provider_name,
            )

        # Execute with fallback chain
        return self._execute_with_fallback(request, decision, context)

    # ------------------------------------------------------------------
    # Execution + fallback
    # ------------------------------------------------------------------

    def _execute_with_fallback(
        self,
        request: AIRequest,
        decision: RoutingDecision,
        context: RoutingContext,
    ) -> AIResponse:
        """Try the selected provider, then each fallback in order."""
        chain = [decision.provider_name, *decision.fallback_chain]
        last_error: Exception | None = None

        for provider_name in chain:
            if provider_name not in self._providers:
                continue

            # Re-enforce hard constraints on fallback candidates
            if not self._provider_satisfies_constraints(provider_name, context):
                logger.warning(
                    "Skipping fallback %s: violates constraints", provider_name
                )
                continue

            try:
                logger.info(
                    "AIGateway routing to %s (reason: %s)",
                    provider_name,
                    decision.reason,
                )
                return self._providers[provider_name].complete(request)
            except ProviderError as exc:
                logger.warning("Provider %s failed: %s", provider_name, exc)
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        raise RoutingError("All compatible providers failed or were unavailable")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_routing_context(request: AIRequest) -> RoutingContext:
        """Extract routing hints from AIRequest.options if present."""
        hints: dict = request.options.get("routing", {})
        return RoutingContext(
            task_type=hints.get("task_type", "general"),
            complexity=hints.get("complexity", "standard"),
            privacy=hints.get("privacy", "normal"),
            quality_requirement=hints.get("quality", "standard"),
            cost_preference=hints.get("cost", "normal"),
            latency_preference=hints.get("latency", "normal"),
            constraints=tuple(hints.get("constraints", ())),
            preferences=tuple(hints.get("preferences", ())),
        )

    def _provider_satisfies_constraints(
        self, provider_name: str, context: RoutingContext
    ) -> bool:
        """Check whether a fallback candidate respects hard constraints."""
        meta = self._metadata.get(provider_name)
        if meta is None:
            return False
        if context.privacy == "local_only" and meta.locality != Locality.LOCAL:
            return False
        if "local_only" in context.constraints and meta.locality != Locality.LOCAL:
            return False
        if "no_paid" in context.constraints and meta.cost_class == CostClass.PAID:
            return False
        return True

    def _legacy_fallback(self) -> RoutingDecision:
        """Backward-compatible fallback when the router has no candidates."""
        preferred = os.environ.get("NAV_AI_PROVIDER", "ollama").lower()
        if preferred in self._providers:
            return RoutingDecision(
                provider_name=preferred, reason="legacy-fallback"
            )
        first = next(iter(self._providers))
        return RoutingDecision(
            provider_name=first, reason="legacy-fallback-first-available"
        )
