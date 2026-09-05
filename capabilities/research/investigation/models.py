"""Investigation models — S15.

Persistent, first-class investigation entities that accumulate
findings, evidence, sources, hypotheses, and open questions
across multiple research interactions.

Entirely additive: reuses existing ResearchFinding, ResearchSource,
ResearchEvidence, and SupportState from core.contracts.research.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.contracts.research import (
    ResearchEvidence,
    ResearchFinding,
    ResearchSource,
    SourceStatus,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InvestigationStatus(str, Enum):
    """Lifecycle state of an investigation."""

    NEW = "new"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class HypothesisStatus(str, Enum):
    """Evaluation state of a hypothesis within an investigation."""

    PROPOSED = "proposed"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hypothesis:
    """A testable proposition within an investigation."""

    hypothesis_id: str
    statement: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    evidence_ids: tuple[str, ...] = ()
    rationale: str | None = None
    created_at: str = ""


@dataclass(frozen=True)
class Investigation:
    """A persistent, evolving research investigation.

    Accumulates sources, evidence, findings, hypotheses, and open
    questions across one or more research interactions.  Reuses the
    existing research data models so that nothing is lost or
    duplicated when a single-shot ResearchResult is folded into a
    long-lived investigation.
    """

    investigation_id: str
    title: str
    objective: str
    status: InvestigationStatus = InvestigationStatus.NEW
    hypotheses: tuple[Hypothesis, ...] = ()
    findings: tuple[ResearchFinding, ...] = ()
    conflicts: tuple[ResearchFinding, ...] = ()
    uncertainties: tuple[ResearchFinding, ...] = ()
    sources: tuple[ResearchSource, ...] = ()
    evidence: tuple[ResearchEvidence, ...] = ()
    open_questions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    project_id: str | None = None
    goal_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # -- helpers ----------------------------------------------------------

    def sources_by_status(self, status: SourceStatus) -> tuple[ResearchSource, ...]:
        return tuple(s for s in self.sources if s.status == status)

    def evidence_for_source(self, source_id: str) -> tuple[ResearchEvidence, ...]:
        return tuple(e for e in self.evidence if e.source_id == source_id)

    def evidence_for_finding(self, finding: ResearchFinding) -> tuple[ResearchEvidence, ...]:
        ids = set(finding.evidence_ids)
        return tuple(e for e in self.evidence if e.evidence_id in ids)


@dataclass(frozen=True)
class InvestigationQuery:
    """Filter criteria for listing investigations."""

    query_text: str | None = None
    status: str | None = None
    tags: tuple[str, ...] = ()
    project_id: str | None = None
    limit: int = 20
