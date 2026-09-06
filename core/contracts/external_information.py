"""
NAV v2 — S23: External Information Contracts.

Defines the request/response boundary for acquiring external information.
These contracts sit between the Research capability and concrete providers.

IMPORTANT:
- Do NOT import provider-specific types here.
- Do NOT couple to any specific external service.
- These contracts must remain stable across provider changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# ---------------------------------------------------------------------------
# Retrieval Status
# ---------------------------------------------------------------------------


class RetrievalStatus(str, Enum):
    """
    Explicit outcome of an external information retrieval attempt.

    S23 §15: Do NOT silently convert failures into empty results.
    S23 §16: No fake research — status must reflect reality.
    """

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    UNAVAILABLE = "unavailable"
    UNAUTHORIZED = "unauthorized"


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalInformationRequest:
    """
    A request to acquire information from an external source.

    S23 §6: Conceptual contract — adapted to NAV conventions after recon.

    Attributes:
        query: The information need expressed as a string.
        source_constraints: Optional hints about acceptable source types.
        result_limit: Maximum number of result items to return.
        freshness_seconds: Optional maximum age of acceptable information.
        request_id: Unique identifier for traceability.
    """

    query: str
    source_constraints: list[str] | None = None
    result_limit: int = 5
    freshness_seconds: int | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not self.query or not self.query.strip():
            raise ValueError("ExternalInformationRequest.query must not be empty.")
        if self.result_limit < 1:
            raise ValueError("ExternalInformationRequest.result_limit must be >= 1.")
        if self.freshness_seconds is not None and self.freshness_seconds < 0:
            raise ValueError("freshness_seconds must be non-negative.")


# ---------------------------------------------------------------------------
# Source Metadata (Provenance — acquisition-time only, S23 §17)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceMetadata:
    """
    Acquisition-time provenance metadata.

    S23 §17: Collect WHERE and WHEN, not trust/reasoning (that is S24).

    Attributes:
        source_name: Human-readable name of the external source.
        source_url: URL or reference locator, if available.
        provider_id: Identifier of the provider that retrieved this.
        retrieved_at: UTC timestamp of retrieval.
        query_echo: The query that produced this result (for traceability).
    """

    source_name: str
    source_url: str | None = None
    provider_id: str = "unknown"
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    query_echo: str | None = None


# ---------------------------------------------------------------------------
# Result Item
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalInformationItem:
    """
    A single piece of retrieved external information.

    Attributes:
        content: The retrieved text/content.
        source: Provenance metadata for this item.
        relevance_hint: Optional provider-supplied relevance signal.
    """

    content: str
    source: SourceMetadata
    relevance_hint: float | None = None


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalInformationResult:
    """
    The complete result of an external information retrieval attempt.

    S23 §5: Must include source/provenance metadata.
    S23 §15: Must report failures explicitly.
    S23 §16: Must never imply retrieval occurred when it did not.

    Attributes:
        status: The explicit outcome of the retrieval.
        items: Retrieved information items (empty if not successful).
        error_message: Human-readable error detail, if applicable.
        provider_id: Which provider was used (or attempted).
        request_id: Echo of the originating request ID.
        completed_at: UTC timestamp of completion.
    """

    status: RetrievalStatus
    items: list[ExternalInformationItem] = field(default_factory=list)
    error_message: str | None = None
    provider_id: str = "unknown"
    request_id: str | None = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_success(self) -> bool:
        return self.status == RetrievalStatus.SUCCESS

    @property
    def has_items(self) -> bool:
        return len(self.items) > 0

    def assert_honest(self) -> None:
        """
        S23 §16 invariant: No fake research.

        If status is not SUCCESS, items must be empty.
        If status is SUCCESS but no items, that is NO_RESULTS.
        """
        if self.status != RetrievalStatus.SUCCESS and self.has_items:
            raise ValueError(
                f"Integrity violation: status={self.status.value} "
                f"but {len(self.items)} items present. "
                "Non-successful retrievals must not carry items."
            )
        if self.status == RetrievalStatus.SUCCESS and not self.has_items:
            raise ValueError(
                "Integrity violation: status=SUCCESS but no items. "
                "Use RetrievalStatus.NO_RESULTS instead."
            )
