"""Investigation continuity models — S16.

Defines the continuation snapshot and resolution models that
enable NAV to resume investigations across sessions.

Key principle: these are DERIVED representations, not competing
sources of truth. The Investigation remains the single source.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvestigationContinuation:
    """A deterministic snapshot: where are we, and what matters next?

    Reconstructed from the Investigation — never persisted separately.
    """

    investigation_id: str
    title: str
    objective: str
    status: str
    progress_summary: str
    established_findings: tuple[str, ...]
    active_hypotheses: tuple[str, ...]
    contradictions: tuple[str, ...]
    uncertainties: tuple[str, ...]
    open_questions: tuple[str, ...]
    recent_activity: str
    suggested_directions: tuple[str, ...]
    source_count: int
    evidence_count: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ResolutionMatch:
    """A single candidate from investigation resolution."""

    investigation_id: str
    title: str
    score: float
    match_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionResult:
    """Outcome of resolving a user query to an investigation.

    confidence: "high" | "medium" | "low" | "none"
    resolved_id is set only when confidence is high or medium.
    """

    matches: tuple[ResolutionMatch, ...]
    confidence: str
    resolved_id: str | None = None
    ambiguity_note: str | None = None
