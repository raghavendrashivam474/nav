"""Research contracts — S7.

Evolved from the S1 sketch to support the full research map that S7
requires: source discovery, retrieval, evidence, provenance, uncertainty,
and conflicts.  The design deliberately separates deterministic concerns
(sources, retrieval metadata, provenance links) from AI-produced content
(claims, findings, synthesis), so the two layers can evolve independently.

This is a documented contract evolution (see docs/s7/completion-report.md).
The previous minimal shape could not represent provenance or uncertainty,
which are non-negotiable requirements for S7.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SourceType(str, Enum):
    """Coarse categorisation of a source.  Extensible; the research layer
    does not switch behaviour on this today, but the field is preserved
    for future specialised retrievers/parsers."""

    ARTICLE = "article"
    PAPER = "paper"
    REPORT = "report"
    DOCUMENTATION = "documentation"
    OFFICIAL_SITE = "official_site"
    PREPRINT = "preprint"
    PATENT = "patent"
    OTHER = "other"


class SourceStatus(str, Enum):
    """Outcome of attempting to retrieve a source."""

    DISCOVERED = "discovered"  # known but not yet fetched
    RETRIEVED = "retrieved"  # fetched successfully
    FAILED = "failed"  # fetch failed (timeout, HTTP error, ...)
    SKIPPED = "skipped"  # excluded (dedup, budget, policy)


class SupportState(str, Enum):
    """Categorical uncertainty label for a finding.

    S7 deliberately avoids inventing numeric confidence scores.  A
    categorical label is honest, easy to audit, and sufficient for
    building the evidence map."""

    SUPPORTED = "supported"  # multiple sources agree
    CONFLICTING = "conflicting"  # sources disagree
    INSUFFICIENT = "insufficient"  # weak or single-source evidence
    UNKNOWN = "unknown"  # no useful evidence found


# ---------------------------------------------------------------------------
# Core data objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchQuery:
    """What NAV is being asked to investigate.

    All bounds (source limits, timeout) are explicit so that every
    research operation is finite and predictable.
    """

    question: str
    scope: str | None = None
    max_sources: int = 8
    max_content_chars: int = 20_000
    timeout_seconds: float = 15.0
    depth: str = "standard"  # "standard" | "deep"
    constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceCandidate:
    """A search hit produced by a SearchProvider, before retrieval."""

    url: str
    title: str
    snippet: str = ""
    source_type: SourceType = SourceType.OTHER
    publisher: str | None = None


@dataclass(frozen=True)
class ResearchSource:
    """A source that NAV has recorded during a research operation.

    A source may be DISCOVERED but not yet RETRIEVED, FAILED, or SKIPPED.
    The status is the deterministic record of what actually happened."""

    source_id: str
    url: str
    canonical_url: str
    title: str
    source_type: SourceType = SourceType.OTHER
    publisher: str | None = None
    status: SourceStatus = SourceStatus.DISCOVERED
    retrieved_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedContent:
    """The (bounded) content pulled from a source, ready for extraction."""

    source_id: str
    text: str
    content_type: str = "text/plain"
    truncated: bool = False


@dataclass(frozen=True)
class ResearchEvidence:
    """A single piece of evidence extracted from a specific source.

    Provenance is a required field: every piece of evidence MUST point
    back to the source it came from.  This is what turns Research into
    a Navigate capability rather than an opaque summarizer."""

    evidence_id: str
    source_id: str
    claim: str
    excerpt: str = ""
    relevance: str = "medium"  # "low" | "medium" | "high"


@dataclass(frozen=True)
class ResearchFinding:
    """A synthesized statement, backed by one or more pieces of evidence."""

    statement: str
    evidence_ids: tuple[str, ...]
    support: SupportState = SupportState.INSUFFICIENT
    notes: str | None = None


@dataclass(frozen=True)
class ResearchResult:
    """The research map: everything NAV learned, with provenance intact."""

    query: ResearchQuery
    sources: tuple[ResearchSource, ...] = ()
    evidence: tuple[ResearchEvidence, ...] = ()
    findings: tuple[ResearchFinding, ...] = ()
    conflicts: tuple[ResearchFinding, ...] = ()
    uncertainties: tuple[ResearchFinding, ...] = ()
    open_questions: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def sources_by_status(self, status: SourceStatus) -> tuple[ResearchSource, ...]:
        return tuple(s for s in self.sources if s.status == status)

    def evidence_for(self, source_id: str) -> tuple[ResearchEvidence, ...]:
        return tuple(e for e in self.evidence if e.source_id == source_id)


# ---------------------------------------------------------------------------
# Protocols for pluggable infrastructure
# ---------------------------------------------------------------------------


class SearchProvider(Protocol):
    """A source of candidate URLs for a research question.

    Implementations may query the web, an academic index, a local
    corpus, or a fake for tests.  The research layer is intentionally
    agnostic."""

    name: str

    def discover(self, query: ResearchQuery) -> list[SourceCandidate]: ...


class SourceRetriever(Protocol):
    """Fetches the content of a source.  Implementations are responsible
    for timeouts, size limits, and error signalling via exceptions."""

    name: str

    def retrieve(
        self, source: ResearchSource, max_chars: int, timeout: float
    ) -> RetrievedContent: ...


# ---------------------------------------------------------------------------
# Capability interface
# ---------------------------------------------------------------------------


class ResearchCapabilityInterface(ABC):
    """Contract for the Research capability.

    Callers hand in a ResearchQuery and receive a fully-formed
    ResearchResult, including any sources that failed and any evidence
    that could not be synthesised into a confident finding."""

    @abstractmethod
    def perform_research(self, query: ResearchQuery) -> ResearchResult:
        pass


# ---------------------------------------------------------------------------
# Small helpers exposed for infrastructure code
# ---------------------------------------------------------------------------


def utcnow() -> datetime:
    """Timezone-aware UTC now — kept in the contract module so all
    research components use one definition."""

    return datetime.now(timezone.utc)
