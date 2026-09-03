"""Ollama provider adapter using local HTTP API.

This enables running open local models (e.g., mistral, llama3) with zero
API keys or costs. Maps NAV contracts to Ollama's native chat API.
"""

from __future__ import annotations

import httpx

from ai.errors import ProviderError
from core.contracts.ai import AIRequest, AIResponse
from core.log import get_logger

logger = get_logger(__name__)

_DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
_DEFAULT_MODEL = "mistral"
_DEFAULT_TIMEOUT = 60.0  # Local generation can take longer on consumer hardware


class OllamaProvider:
    """Translates NAV AIRequest/AIResponse to/from the Ollama Local Chat API."""

    def __init__(
        self,
        base_url: str = _DEFAULT_OLLAMA_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout = timeout

    def complete(self, request: AIRequest) -> AIResponse:
        """Send an AIRequest to Ollama and return a normalized AIResponse."""
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }

        logger.info(
            "Ollama local request initiated (model=%s, url=%s)", self._model, self._base_url
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(self._base_url, json=payload)
        except httpx.TimeoutException as exc:
            logger.error("Ollama request timed out: %s", exc)
            raise ProviderError(f"Ollama request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            logger.error("Ollama network error: %s", exc)
            raise ProviderError(f"Ollama network error: {exc}") from exc

        if response.status_code >= 400:
            raise ProviderError(f"Ollama API error (HTTP {response.status_code}): {response.text}")

        return self._parse_response(response.json())

    def _parse_response(self, data: dict) -> AIResponse:
        try:
            content = data["message"]["content"] or ""
            model_used = data.get("model", self._model)
            # Map Ollama performance stats to usage keys
            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            }
        except KeyError as exc:
            raise ProviderError(f"Unexpected Ollama response structure: {exc}") from exc

        logger.info("Ollama response received (model=%s)", model_used)
        return AIResponse(
            content=content,
            model_used=model_used,
            usage=usage,
        )
