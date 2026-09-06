"""
NAV v2 — S23: External Information Capability.

This is the integration point between NAV's orchestration layer
and the external information provider system.

S23 §5 required behavior:
 1. Receive the request
 2. Pass through normal capability boundary
 3. Enforce existing security (S20)
 4. Invoke external-information capability
 5. Use an approved provider
 6. Retrieve information
 7. Return structured results
 8. Include source/provenance metadata
 9. Report failures explicitly
10. Return control to caller

S23 §16: NEVER imply information was retrieved when it was not.
"""

from __future__ import annotations

import logging

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

    This class is the single entry point for external retrieval.
    It delegates to providers via the registry and enforces
    the S23 honesty invariants.

    Security Note (S23 §14):
        This capability does NOT perform its own authorization.
        Authorization is handled by the S20 security plane BEFORE
        this capability is invoked by the Orchestrator.
        If you reach this code, authorization has already passed.
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def acquire(
        self,
        request: ExternalInformationRequest,
        provider_id: str | None = None,
    ) -> ExternalInformationResult:
        """
        Acquire external information for the given request.

        Args:
            request: The external information request.
            provider_id: Optional specific provider. Uses default if None.

        Returns:
            ExternalInformationResult with explicit status.
        """
        logger.info(
            "S23: External information request received. query=%r, provider=%s",
            request.query,
            provider_id or "default",
        )

        # --- Validate request ---
        if not request.query or not request.query.strip():
            return ExternalInformationResult(
                status=RetrievalStatus.INVALID_REQUEST,
                provider_id=provider_id or "none",
                request_id=request.request_id,
                error_message="Empty query.",
            )

        # --- Resolve provider ---
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

        # --- Execute retrieval ---
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

        # --- Enforce honesty invariant (S23 §16) ---
        try:
            result.assert_honest()
        except ValueError as integrity_error:
            logger.critical(
                "S23: INTEGRITY VIOLATION from provider %s: %s",
                provider.provider_id,
                integrity_error,
            )
            # Override the dishonest result
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
