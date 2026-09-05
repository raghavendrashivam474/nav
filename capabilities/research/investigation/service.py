"""Investigation service layer — S15.

Manages the lifecycle of persistent research investigations.
Composes with the existing ResearchService to execute research
and fold results into long-lived investigation records.

Key principle: Investigation owns accumulated knowledge;
ResearchService owns single-shot execution.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Protocol

from capabilities.research.investigation.models import (
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationQuery,
    InvestigationStatus,
)
from capabilities.research.investigation.repository import InvestigationRepository
from core.contracts.context import NavContext
from core.contracts.research import (
    ResearchFinding,
    ResearchQuery,
    ResearchResult,
    SupportState,
)
from core.log import get_logger

logger = get_logger(__name__)


class ResearchExecutor(Protocol):
    """Protocol for executing research queries."""

    def execute_research(self, query: ResearchQuery) -> ResearchResult: ...


class InvestigationService:
    """High-level investigation lifecycle management."""

    def __init__(
        self,
        repository: InvestigationRepository,
        research_service: ResearchExecutor | None = None,
    ) -> None:
        self._repo = repository
        self._repo.initialize()
        self._research_service = research_service

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create_investigation(
        self,
        title: str,
        objective: str,
        tags: tuple[str, ...] = (),
        project_id: str | None = None,
        goal_id: str | None = None,
    ) -> Investigation:
        """Create a new investigation in NEW status."""
        now = datetime.now(timezone.utc).isoformat()
        inv = Investigation(
            investigation_id=f"inv_{uuid.uuid4().hex[:12]}",
            title=title,
            objective=objective,
            status=InvestigationStatus.NEW,
            tags=tags,
            project_id=project_id,
            goal_id=goal_id,
            created_at=now,
            updated_at=now,
        )
        self._repo.save(inv)
        logger.info("Created investigation %s: %s", inv.investigation_id, title)
        return inv

    def create_from_context(
        self,
        context: NavContext,
        title: str,
        objective: str | None = None,
        tags: tuple[str, ...] = (),
    ) -> Investigation:
        """Create an investigation informed by the current NavContext.

        Derives project_id, goal_id, and additional tags from the
        user's personal context (S12) without mutating it.
        """
        project_id: str | None = None
        goal_id: str | None = None
        context_tags: list[str] = list(tags)

        pc = context.personal_context
        if pc is not None:
            focus = pc.current_focus
            if focus is not None:
                project_id = focus.project_id
                goal_id = focus.goal_id
                if focus.topic and focus.topic not in context_tags:
                    context_tags.append(focus.topic)

            for p in pc.projects:
                if p.project_id == project_id and p.name:
                    if p.name not in context_tags:
                        context_tags.append(p.name)

        return self.create_investigation(
            title=title,
            objective=objective or title,
            tags=tuple(context_tags),
            project_id=project_id,
            goal_id=goal_id,
        )

    # ------------------------------------------------------------------
    # Research execution
    # ------------------------------------------------------------------

    def conduct_research(
        self,
        investigation_id: str,
        query_override: str | None = None,
        depth: str = "standard",
        max_sources: int = 8,
    ) -> Investigation:
        """Execute a research query and merge results into the investigation."""
        inv = self._repo.get(investigation_id)
        if inv is None:
            raise ValueError(f"Investigation {investigation_id} not found")
        if self._research_service is None:
            raise RuntimeError("No ResearchService configured for investigation research")

        question = query_override or inv.objective
        query = ResearchQuery(question=question, depth=depth, max_sources=max_sources)

        result = self._research_service.execute_research(query)

        merged = self._merge_results(inv, result)

        if merged.status == InvestigationStatus.NEW:
            merged = replace(merged, status=InvestigationStatus.ACTIVE)

        merged = replace(merged, updated_at=datetime.now(timezone.utc).isoformat())
        self._repo.update(merged)
        logger.info(
            "Research merged into investigation %s: %d new findings",
            investigation_id,
            len(result.findings),
        )
        return merged

    # ------------------------------------------------------------------
    # Hypothesis management
    # ------------------------------------------------------------------

    def add_hypothesis(
        self,
        investigation_id: str,
        statement: str,
        rationale: str | None = None,
    ) -> Investigation:
        inv = self._require(investigation_id)
        hyp = Hypothesis(
            hypothesis_id=f"hyp_{uuid.uuid4().hex[:8]}",
            statement=statement,
            rationale=rationale,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        updated = replace(
            inv,
            hypotheses=inv.hypotheses + (hyp,),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.update(updated)
        return updated

    def update_hypothesis(
        self,
        investigation_id: str,
        hypothesis_id: str,
        status: HypothesisStatus | str,
        evidence_ids: tuple[str, ...] | None = None,
        rationale: str | None = None,
    ) -> Investigation:
        inv = self._require(investigation_id)
        if isinstance(status, str):
            status = HypothesisStatus(status)

        new_hyps: list[Hypothesis] = []
        found = False
        for h in inv.hypotheses:
            if h.hypothesis_id == hypothesis_id:
                found = True
                h = replace(h, status=status)
                if evidence_ids is not None:
                    h = replace(h, evidence_ids=evidence_ids)
                if rationale is not None:
                    h = replace(h, rationale=rationale)
            new_hyps.append(h)

        if not found:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        updated = replace(
            inv,
            hypotheses=tuple(new_hyps),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.update(updated)
        return updated

    # ------------------------------------------------------------------
    # Finding & question management
    # ------------------------------------------------------------------

    def add_finding(
        self,
        investigation_id: str,
        statement: str,
        evidence_ids: tuple[str, ...] = (),
        support: SupportState | str = SupportState.SUPPORTED,
        notes: str | None = None,
    ) -> Investigation:
        inv = self._require(investigation_id)
        if isinstance(support, str):
            support = SupportState(support)
        finding = ResearchFinding(
            statement=statement,
            evidence_ids=evidence_ids,
            support=support,
            notes=notes,
        )
        updated = replace(
            inv,
            findings=inv.findings + (finding,),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.update(updated)
        return updated

    def add_open_question(self, investigation_id: str, question: str) -> Investigation:
        inv = self._require(investigation_id)
        if question in inv.open_questions:
            return inv
        updated = replace(
            inv,
            open_questions=inv.open_questions + (question,),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.update(updated)
        return updated

    def resolve_open_question(self, investigation_id: str, question: str) -> Investigation:
        inv = self._require(investigation_id)
        remaining = tuple(q for q in inv.open_questions if q != question)
        if len(remaining) == len(inv.open_questions):
            return inv  # not found, no-op
        updated = replace(
            inv,
            open_questions=remaining,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.update(updated)
        return updated

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def set_status(self, investigation_id: str, status: InvestigationStatus | str) -> Investigation:
        inv = self._require(investigation_id)
        if isinstance(status, str):
            status = InvestigationStatus(status)
        updated = replace(
            inv,
            status=status,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.update(updated)
        logger.info("Investigation %s -> %s", investigation_id, status.value)
        return updated

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_investigation(self, investigation_id: str) -> Investigation | None:
        return self._repo.get(investigation_id)

    def list_investigations(self, query: InvestigationQuery | None = None) -> list[Investigation]:
        return self._repo.find(query or InvestigationQuery())

    def delete_investigation(self, investigation_id: str) -> bool:
        ok = self._repo.delete(investigation_id)
        if ok:
            logger.info("Deleted investigation %s", investigation_id)
        return ok

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require(self, investigation_id: str) -> Investigation:
        inv = self._repo.get(investigation_id)
        if inv is None:
            raise ValueError(f"Investigation {investigation_id} not found")
        return inv

    @staticmethod
    def _merge_results(inv: Investigation, result: ResearchResult) -> Investigation:
        """Fold a ResearchResult into an existing Investigation.

        Deduplicates sources by source_id, evidence by evidence_id,
        findings by statement text, and open questions by exact match.
        """
        # --- sources ---
        existing_source_ids = {s.source_id for s in inv.sources}
        new_sources = [s for s in result.sources if s.source_id not in existing_source_ids]

        # --- evidence ---
        existing_ev_ids = {e.evidence_id for e in inv.evidence}
        new_evidence = [e for e in result.evidence if e.evidence_id not in existing_ev_ids]

        # --- findings ---
        existing_statements = {f.statement for f in inv.findings}
        new_findings = [f for f in result.findings if f.statement not in existing_statements]

        # --- conflicts ---
        existing_conflicts = {f.statement for f in inv.conflicts}
        new_conflicts = [f for f in result.conflicts if f.statement not in existing_conflicts]

        # --- uncertainties ---
        existing_unc = {f.statement for f in inv.uncertainties}
        new_unc = [f for f in result.uncertainties if f.statement not in existing_unc]

        # --- open questions ---
        existing_oq = set(inv.open_questions)
        new_oq = [q for q in result.open_questions if q not in existing_oq]

        return replace(
            inv,
            sources=inv.sources + tuple(new_sources),
            evidence=inv.evidence + tuple(new_evidence),
            findings=inv.findings + tuple(new_findings),
            conflicts=inv.conflicts + tuple(new_conflicts),
            uncertainties=inv.uncertainties + tuple(new_unc),
            open_questions=inv.open_questions + tuple(new_oq),
        )
