"""
NAV v2 — S23: Static External Information Provider.

This is the FIRST provider — intentionally narrow.
It returns pre-configured responses for known queries.

Purpose:
- Validates the full S23 pipeline end-to-end
- Provides deterministic behavior for testing
- Serves as the template for real providers (S24+)

S23 §8: "The first provider can be intentionally narrow."
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.contracts.external_information import (
    ExternalInformationItem,
    ExternalInformationRequest,
    ExternalInformationResult,
    RetrievalStatus,
    SourceMetadata,
)


class StaticInformationProvider:
    """
    A deterministic provider for validation and testing.

    Returns pre-configured results for known query patterns.
    Returns NO_RESULTS for unknown queries.
    Never fabricates information.
    """

    def __init__(
        self,
        known_responses: dict[str, str] | None = None,
    ) -> None:
        self._known_responses: dict[str, str] = known_responses or {
            "nav version": (
                "NAV v2 is the Personal Intelligence major version, "
                "currently in early sprint development."
            ),
            "s23 status": (
                "S23 implements the External Information Capability, "
                "giving NAV a controlled path to acquire external data."
            ),
        }

    @property
    def provider_id(self) -> str:
        return "static-provider-v1"

    def retrieve(
        self,
        request: ExternalInformationRequest,
    ) -> ExternalInformationResult:
        query_lower = request.query.strip().lower()

        # Check for known responses
        for key, content in self._known_responses.items():
            if key in query_lower:
                item = ExternalInformationItem(
                    content=content,
                    source=SourceMetadata(
                        source_name="Static Knowledge Base",
                        source_url=None,
                        provider_id=self.provider_id,
                        retrieved_at=datetime.now(timezone.utc),
                        query_echo=request.query,
                    ),
                    relevance_hint=1.0,
                )
                return ExternalInformationResult(
                    status=RetrievalStatus.SUCCESS,
                    items=[item],
                    provider_id=self.provider_id,
                    request_id=request.request_id,
                )

        # No match — honest NO_RESULTS, not fake success
        return ExternalInformationResult(
            status=RetrievalStatus.NO_RESULTS,
            items=[],
            provider_id=self.provider_id,
            request_id=request.request_id,
            error_message=f"No static response for query: {request.query!r}",
        )

    def is_available(self) -> bool:
        return True
