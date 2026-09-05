"""Investigation continuity service — S16.

Provides investigation resolution (matching user intent to an
existing investigation) and continuation reconstruction (building
a deterministic snapshot of where the investigation stands).

Key principle: suggest, never silently substitute.
"""

from __future__ import annotations

from capabilities.research.investigation.continuity.models import (
    InvestigationContinuation,
    ResolutionMatch,
    ResolutionResult,
)
from capabilities.research.investigation.models import (
    Investigation,
    InvestigationQuery,
    InvestigationStatus,
)
from capabilities.research.investigation.repository import InvestigationRepository
from core.log import get_logger

logger = get_logger(__name__)


class InvestigationContinuityService:
    """Resolves and reconstructs investigation state for continuation."""

    def __init__(self, repository: InvestigationRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve_investigation(
        self,
        query_text: str,
        project_id: str | None = None,
        goal_id: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> ResolutionResult:
        """Match a user's request to an existing investigation.

        Deterministic scoring — no LLM, no vector search.
        """
        query_text = query_text.strip()

        # 1. Exact ID match
        if query_text.startswith("inv_"):
            inv = self._repo.get(query_text)
            if inv is not None:
                return ResolutionResult(
                    matches=(
                        ResolutionMatch(
                            investigation_id=inv.investigation_id,
                            title=inv.title,
                            score=1.0,
                            match_reasons=("exact_id",),
                        ),
                    ),
                    confidence="high",
                    resolved_id=inv.investigation_id,
                )

        # 2. Text search via repository
        candidates = self._repo.find(
            InvestigationQuery(query_text=query_text, limit=20)
        )

        # Fallback: search by project if text search yielded nothing
        if not candidates and project_id:
            candidates = self._repo.find(
                InvestigationQuery(project_id=project_id, limit=20)
            )

        if not candidates:
            return ResolutionResult(
                matches=(),
                confidence="none",
                ambiguity_note="No matching investigation found.",
            )

        # 3. Score candidates
        query_lower = query_text.lower()
        scored: list[ResolutionMatch] = []

        for inv in candidates:
            score = 0.0
            reasons: list[str] = []

            title_lower = inv.title.lower()
            if query_lower == title_lower:
                score += 0.6
                reasons.append("exact_title")
            elif query_lower in title_lower or title_lower in query_lower:
                score += 0.4
                reasons.append("title_substring")

            if query_lower in inv.objective.lower():
                score += 0.2
                reasons.append("objective_match")

            for tag in tags:
                if tag.lower() in [t.lower() for t in inv.tags]:
                    score += 0.15
                    reasons.append(f"tag:{tag}")

            if project_id and inv.project_id == project_id:
                score += 0.15
                reasons.append("project_match")

            if goal_id and inv.goal_id == goal_id:
                score += 0.1
                reasons.append("goal_match")

            if inv.status in (InvestigationStatus.ACTIVE, InvestigationStatus.NEW):
                score += 0.05
                reasons.append("active_status")

            if score > 0 and reasons:
                scored.append(
                    ResolutionMatch(
                        investigation_id=inv.investigation_id,
                        title=inv.title,
                        score=round(score, 2),
                        match_reasons=tuple(reasons),
                    )
                )

        if not scored:
            return ResolutionResult(
                matches=(),
                confidence="none",
                ambiguity_note="No confident match found.",
            )

        scored.sort(key=lambda m: m.score, reverse=True)
        top = scored[0]

        # 4. Ambiguity check
        if len(scored) > 1 and scored[1].score >= top.score * 0.8:
            return ResolutionResult(
                matches=tuple(scored[:3]),
                confidence="low",
                ambiguity_note=(
                    f"Multiple investigations match. "
                    f"Top: '{scored[0].title}', '{scored[1].title}'."
                ),
            )

        confidence = "high" if top.score >= 0.4 else "medium"
        return ResolutionResult(
            matches=tuple(scored[:3]),
            confidence=confidence,
            resolved_id=(
                top.investigation_id
                if confidence in ("high", "medium")
                else None
            ),
        )

    # ------------------------------------------------------------------
    # Continuation reconstruction
    # ------------------------------------------------------------------

    def build_continuation(
        self, investigation: Investigation
    ) -> InvestigationContinuation:
        """Deterministic snapshot from an Investigation. No LLM."""
        established = tuple(
            f.statement
            for f in investigation.findings
            if f.support.value == "supported"
        )

        active_hyps = tuple(
            f"[{h.status.value}] {h.statement}"
            for h in investigation.hypotheses
            if h.status.value in ("proposed", "supported", "inconclusive")
        )

        contradictions = tuple(f.statement for f in investigation.conflicts)
        uncertainties = tuple(f.statement for f in investigation.uncertainties)

        # Recent activity
        recent = "No recorded activity."
        if investigation.activity_log:
            latest = investigation.activity_log[-1]
            recent = (
                f"{latest.activity_type.value}: "
                f"{latest.description} ({latest.timestamp})"
            )

        # Suggested directions
        suggestions: list[str] = []
        if investigation.open_questions:
            suggestions.append(f"Investigate: {investigation.open_questions[0]}")
        if investigation.uncertainties:
            suggestions.append(
                f"Resolve uncertainty: {investigation.uncertainties[0].statement}"
            )
        if investigation.conflicts:
            suggestions.append(
                f"Resolve conflict: {investigation.conflicts[0].statement}"
            )
        if not suggestions:
            suggestions.append("Investigation appears complete or needs new direction.")

        progress = (
            f"{len(investigation.findings)} findings, "
            f"{len(investigation.hypotheses)} hypotheses, "
            f"{len(investigation.open_questions)} open questions, "
            f"{len(investigation.sources)} sources"
        )

        return InvestigationContinuation(
            investigation_id=investigation.investigation_id,
            title=investigation.title,
            objective=investigation.objective,
            status=investigation.status.value,
            progress_summary=progress,
            established_findings=established,
            active_hypotheses=active_hyps,
            contradictions=contradictions,
            uncertainties=uncertainties,
            open_questions=investigation.open_questions,
            recent_activity=recent,
            suggested_directions=tuple(suggestions),
            source_count=len(investigation.sources),
            evidence_count=len(investigation.evidence),
            created_at=investigation.created_at,
            updated_at=investigation.updated_at,
        )

    # ------------------------------------------------------------------
    # Combined resume
    # ------------------------------------------------------------------

    def resume(
        self,
        query_text: str,
        project_id: str | None = None,
        goal_id: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> tuple[ResolutionResult, InvestigationContinuation | None]:
        """Resolve + reconstruct in one step.

        Returns (resolution, continuation).
        continuation is None when resolution fails or is ambiguous.
        """
        resolution = self.resolve_investigation(
            query_text=query_text,
            project_id=project_id,
            goal_id=goal_id,
            tags=tags,
        )

        if resolution.resolved_id is None:
            return resolution, None

        inv = self._repo.get(resolution.resolved_id)
        if inv is None:
            return resolution, None

        return resolution, self.build_continuation(inv)
