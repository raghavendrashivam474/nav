"""Default AIGateway implementation.

Delegates to either OllamaProvider or OpenAIProvider based on environment configuration.
NAV Core and capabilities remain fully decoupled from the active provider.
"""

from __future__ import annotations

import os

from ai.errors import ConfigurationError
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.openai_provider import OpenAIProvider
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.log import get_logger

logger = get_logger(__name__)


class DefaultAIGateway(AIGateway):
    """Concrete AIGateway backed by a dynamically selected provider.

    S3 supports 'ollama' (default local Mistral) and 'openai' (frontier APIs).
    """

    def __init__(self) -> None:
        self._provider_type = os.environ.get("NAV_AI_PROVIDER", "ollama").lower()

        if self._provider_type == "ollama":
            url = os.environ.get("NAV_OLLAMA_URL", "http://localhost:11434/api/chat")
            model = os.environ.get("NAV_OLLAMA_MODEL", "mistral")
            self._provider: OllamaProvider | OpenAIProvider = OllamaProvider(
                base_url=url, model=model
            )
            logger.info("DefaultAIGateway initialized (provider=Ollama, model=%s)", model)

        elif self._provider_type == "openai":
            api_key = os.environ.get("NAV_OPENAI_API_KEY", "")
            model = os.environ.get("NAV_OPENAI_MODEL", "gpt-4o-mini")
            if not api_key:
                raise ConfigurationError(
                    "NAV_OPENAI_API_KEY is not set but 'openai' provider was selected."
                )
            self._provider = OpenAIProvider(api_key=api_key, model=model)
            logger.info("DefaultAIGateway initialized (provider=OpenAI, model=%s)", model)

        else:
            raise ConfigurationError(f"Unsupported AI provider: '{self._provider_type}'")

    def generate(self, request: AIRequest) -> AIResponse:
        """Route request through the selected provider."""
        logger.info(
            "AIGateway.generate called via %s (%d messages)",
            self._provider_type,
            len(request.messages),
        )
        return self._provider.complete(request)
