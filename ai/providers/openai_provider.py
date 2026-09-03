"""OpenAI provider adapter using raw HTTP via httpx.

This is an S3 implementation choice, not a NAV architectural commitment.
The provider translates between NAV AI contracts and the OpenAI HTTP API,
keeping all vendor-specific logic isolated here.
"""

from __future__ import annotations

import httpx

from ai.errors import ConfigurationError, ProviderError
from core.contracts.ai import AIRequest, AIResponse
from core.log import get_logger

logger = get_logger(__name__)

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TIMEOUT = 30.0


class OpenAIProvider:
    """Translates NAV AIRequest/AIResponse to/from the OpenAI Chat API."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ConfigurationError("OpenAI API key is empty. Set NAV_OPENAI_API_KEY.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def complete(self, request: AIRequest) -> AIResponse:
        """Send an AIRequest to OpenAI and return a normalised AIResponse."""
        payload = self._build_payload(request)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        logger.info("OpenAI request initiated (model=%s)", self._model)

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    _OPENAI_API_URL,
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            logger.error("OpenAI request timed out: %s", exc)
            raise ProviderError(f"OpenAI request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            logger.error("OpenAI network error: %s", exc)
            raise ProviderError(f"OpenAI network error: {exc}") from exc

        if response.status_code == 401:
            raise ConfigurationError(
                "OpenAI rejected the API key (HTTP 401). Check NAV_OPENAI_API_KEY."
            )
        if response.status_code == 429:
            raise ProviderError("OpenAI rate limit exceeded (HTTP 429).")
        if response.status_code >= 500:
            raise ProviderError(f"OpenAI server error (HTTP {response.status_code}).")
        if response.status_code >= 400:
            raise ProviderError(f"OpenAI API error (HTTP {response.status_code}): {response.text}")

        return self._parse_response(response.json())

    # ------------------------------------------------------------------
    # Translation helpers (vendor-specific logic stays here)
    # ------------------------------------------------------------------

    def _build_payload(self, request: AIRequest) -> dict:
        payload: dict = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def _parse_response(self, data: dict) -> AIResponse:
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"] or ""
            model_used = data.get("model", self._model)
            usage = data.get("usage", {})
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected OpenAI response structure: {exc}") from exc

        logger.info("OpenAI response received (model=%s)", model_used)
        return AIResponse(
            content=content,
            model_used=model_used,
            usage=usage,
        )
