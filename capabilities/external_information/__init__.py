"""
NAV v2 — S23: External Information Capability Package.
"""

from capabilities.external_information.provider_protocol import (
    ExternalInformationProvider,
)
from capabilities.external_information.registry import ProviderRegistry
from capabilities.external_information.static_provider import (
    StaticInformationProvider,
)
from capabilities.external_information.wikipedia_provider import (
    WikipediaProvider,
)

__all__ = [
    "ExternalInformationProvider",
    "ProviderRegistry",
    "StaticInformationProvider",
    "WikipediaProvider",
]
