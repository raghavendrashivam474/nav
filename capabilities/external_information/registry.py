"""
NAV v2 — S23: Provider Registry.

Manages available ExternalInformationProvider instances.
The capability layer queries this registry — it does not hardcode providers.

S23 §7: "A provider should be replaceable without changing NAV's core logic."
"""

from __future__ import annotations

from capabilities.external_information.provider_protocol import (
    ExternalInformationProvider,
)


class ProviderRegistry:
    """
    Registry of available external information providers.

    Supports:
    - Registration of multiple providers
    - Selection of a default provider
    - Availability checking
    - Future: constraint-based provider selection
    """

    def __init__(self) -> None:
        self._providers: dict[str, ExternalInformationProvider] = {}
        self._default_provider_id: str | None = None

    def register(
        self,
        provider: ExternalInformationProvider,
        set_default: bool = False,
    ) -> None:
        """Register a provider. Optionally set as default."""
        pid = provider.provider_id
        if pid in self._providers:
            raise ValueError(f"Provider already registered: {pid}")
        self._providers[pid] = provider
        if set_default or self._default_provider_id is None:
            self._default_provider_id = pid

    def get_provider(
        self,
        provider_id: str | None = None,
    ) -> ExternalInformationProvider:
        """
        Retrieve a provider by ID, or the default.

        Raises:
            ValueError: If no matching provider is found.
            RuntimeError: If no providers are registered.
        """
        if not self._providers:
            raise RuntimeError("No external information providers registered.")

        target_id = provider_id or self._default_provider_id
        if target_id is None:
            raise ValueError("No default provider set and no ID specified.")

        provider = self._providers.get(target_id)
        if provider is None:
            raise ValueError(f"Unknown provider: {target_id}")

        return provider

    def get_available_provider(
        self,
        provider_id: str | None = None,
    ) -> ExternalInformationProvider:
        """Get a provider and verify it is available."""
        provider = self.get_provider(provider_id)
        if not provider.is_available():
            # Caller should handle UNAVAILABLE — this is a convenience check
            raise RuntimeError(f"Provider {provider.provider_id} is not available.")
        return provider

    @property
    def registered_ids(self) -> list[str]:
        return list(self._providers.keys())

    @property
    def default_provider_id(self) -> str | None:
        return self._default_provider_id
