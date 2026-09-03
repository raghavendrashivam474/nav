"""NAV AI error hierarchy.

All AI-layer errors derive from AIError so that NAV Core never sees
provider-specific exception types (e.g., OpenAIAuthenticationError).
Provider adapters are responsible for translating external errors into
these NAV-level types.
"""


class AIError(Exception):
    """Base exception for all AI-layer errors."""


class ConfigurationError(AIError):
    """Missing or invalid AI configuration (e.g., absent API key)."""


class ProviderError(AIError):
    """Error originating from the AI provider or network layer."""
