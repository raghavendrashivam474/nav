"""Structural protocol for AI providers.

Both OllamaProvider and OpenAIProvider satisfy this protocol without
modification because they already implement complete(AIRequest) -> AIResponse.
"""

from __future__ import annotations

from typing import Protocol

from core.contracts.ai import AIRequest, AIResponse


class AIProvider(Protocol):
    """Any object with a complete() method matching this signature."""

    def complete(self, request: AIRequest) -> AIResponse: ...
