"""
NAV v2 — S23: External Information Provider Protocol.

S23 §7: All providers must implement this interface.
The capability layer talks to this Protocol, never to concrete providers.

To add a new provider:
1. Implement ExternalInformationProvider
2. Register it with the capability
3. Do NOT modify any Core or Orchestrator code
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.contracts.external_information import (
    ExternalInformationRequest,
    ExternalInformationResult,
)


@runtime_checkable
class ExternalInformationProvider(Protocol):
    """
    Replaceable provider for external information retrieval.

    Implementations must:
    - Return ExternalInformationResult with explicit status
    - Never raise unhandled exceptions (catch and return PROVIDER_ERROR)
    - Never fabricate results (S23 §16)
    - Include source metadata in every returned item (S23 §17)
    """

    @property
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        ...

    def retrieve(
        self,
        request: ExternalInformationRequest,
    ) -> ExternalInformationResult:
        """
        Execute an external information retrieval.

        Args:
            request: The information request.

        Returns:
            ExternalInformationResult with explicit status and items.
        """
        ...

    def is_available(self) -> bool:
        """
        Check whether this provider is currently operational.

        Returns:
            True if the provider can accept requests.
        """
        ...
