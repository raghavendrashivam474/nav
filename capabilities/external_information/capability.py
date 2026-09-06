"""
NAV v2 — S23: External Information Capability.

This is the integration point between NAV's orchestration layer
and the external information provider system.
"""

from __future__ import annotations

import logging
from typing import Any

from capabilities.external_information.registry import ProviderRegistry
from core.contracts.external_information import (
    ExternalInformationRequest,
    ExternalInformationResult,
    RetrievalStatus,
)

logger = logging.getLogger(__name__)


class ExternalInformationCapability:
    """
    NAV capability for acquiring external information.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def execute(self, action_data: dict[str, Any], context: Any = None) -> dict[str, Any]:
        """
        Orchestrator interface entry point.
        Converts generic orchestrator dict packets into strict contracts,
        executes, and returns the response serialized to a dictionary.
        """
        query = action_data.get("query", "")
        result_limit = action_data.get("result_limit", 5)
        provider_id = action_data.get("provider_id")
        request_id = action_data.get("request_id")

        try:
            req = ExternalInformationRequest(
                query=query,
                result_limit=result_limit,
                request_id=request_id,
            )
        except ValueError as exc:
            return {
                "status": RetrievalStatus.INVALID_REQUEST.value,
                "items": [],
                "error_message": str(exc),
                "provider_id": provider_id or "none",
            }

        result = self.acquire(req, provider_id=provider_id)

        # Serialize the structured response back to the orchestrator dictionary format
        return {
            "status": result.status.value,
            "provider_id": result.provider_id,
            "request_id": result.request_id,
            "error_message": result.error_message,
            "items": [
                {
                    "content": item.content,
                    "source": {
                        "source_name": item.source.source_name,
                        "source_url": item.source.source_url,
                        "provider_id": item.source.provider_id,
                        "retrieved_at": item.source.retrieved_at.isoformat(),
                        "query_echo": item.source.query_echo,
                    },
                    "relevance_hint": item.relevance_hint,
                }
                for item in result.items
            ],
        }

    def acquire(
        self,
        request: ExternalInformationRequest,
        provider_id: str | None = None,
    ) -> ExternalInformationResult:
        """
        Internal domain execution path.
        """
        logger.info(
            "S23: External information request received. query=%r, provider=%s",
            request.query,
            provider_id or "default",
        )

        if not request.query or not request.query.strip():
            return ExternalInformationResult(
                status=RetrievalStatus.INVALID_REQUEST,
                provider_id=provider_id or "none",
                request_id=request.request_id,
                error_message="Empty query.",
            )

        try:
            provider = self._registry.get_available_provider(provider_id)
        except RuntimeError as exc:
            logger.warning("S23: Provider unavailable: %s", exc)
            return ExternalInformationResult(
                status=RetrievalStatus.UNAVAILABLE,
                provider_id=provider_id or "none",
                request_id=request.request_id,
                error_message=str(exc),
            )
        except ValueError as exc:
            logger.warning("S23: Provider error: %s", exc)
            return ExternalInformationResult(
                status=RetrievalStatus.INVALID_REQUEST,
                provider_id=provider_id or "none",
                request_id=request.request_id,
                error_message=str(exc),
            )

        try:
            result = provider.retrieve(request)
        except TimeoutError:
            logger.error("S23: Provider timeout for query=%r", request.query)
            return ExternalInformationResult(
                status=RetrievalStatus.TIMEOUT,
                provider_id=provider.provider_id,
                request_id=request.request_id,
                error_message="Provider timed out.",
            )
        except Exception as exc:
            logger.exception(
                "S23: Provider raised unexpected error for query=%r",
                request.query,
            )
            return ExternalInformationResult(
                status=RetrievalStatus.PROVIDER_ERROR,
                provider_id=provider.provider_id,
                request_id=request.request_id,
                error_message=f"Provider error: {type(exc).__name__}: {exc}",
            )

        try:
            result.assert_honest()
        except ValueError as integrity_error:
            logger.critical(
                "S23: INTEGRITY VIOLATION from provider %s: %s",
                provider.provider_id,
                integrity_error,
            )
            return ExternalInformationResult(
                status=RetrievalStatus.PROVIDER_ERROR,
                provider_id=provider.provider_id,
                request_id=request.request_id,
                error_message=(f"Provider returned inconsistent result: {integrity_error}"),
            )

        logger.info(
            "S23: Retrieval complete. status=%s, items=%d, provider=%s",
            result.status.value,
            len(result.items),
            result.provider_id,
        )

        return result
