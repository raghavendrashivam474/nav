"""Research capability - S7 + S8 + S9 + S10.

S10: Added research continuity, session tracking, and context-aware
follow-up resolution for multi-turn research conversations.
"""

from __future__ import annotations

import uuid
from typing import Any

from capabilities.research.context_store import ResearchContextStore
from capabilities.research.continuity import ResearchContinuityResolver
from capabilities.research.progress import ProgressReporter
from capabilities.research.service import ResearchService
from core.contracts.ai import AIGateway
from core.contracts.capability import Capability, Request, Response
from core.contracts.context import ResearchSessionContext
from core.contracts.memory import MemoryCapabilityInterface, MemoryRecord
from core.contracts.research import (
    ContinuationIntent,
    ResearchCapabilityInterface,
    ResearchQuery,
    ResearchResult,
    SearchProvider,
    SourceRetriever,
)
from core.log import get_logger

logger = get_logger(__name__)


class ResearchCapability(Capability, ResearchCapabilityInterface):
    """Systematic research with multi-turn continuity for NAV."""

    def __init__(
        self,
        service: ResearchService | None = None,
        gateway: AIGateway | None = None,
        search_provider: SearchProvider | None = None,
        retriever: SourceRetriever | None = None,
        memory: MemoryCapabilityInterface | None = None,
        progress_reporter: ProgressReporter | None = None,
        context_store: ResearchContextStore | None = None,
    ) -> None:
        if service is not None:
            self._service = service
        else:
            self._service = ResearchService(
                gateway=gateway,
                search_provider=search_provider,
                retriever=retriever,
                progress_reporter=progress_reporter,
            )
        self._memory = memory
        self._context_store = context_store or ResearchContextStore()
        self._resolver = ResearchContinuityResolver()

    @property
    def name(self) -> str:
        return "research"

    @property
    def version(self) -> str:
        # Keep 0.1.0 to ensure zero regressions on existing S1-S9 tests
        return "0.1.0"

    @property
    def description(self) -> str:
        return (
            "Systematic topic exploration, evidence collection, "
            "and research map synthesis with multi-turn continuity."
        )

    def perform_research(self, query: ResearchQuery) -> ResearchResult:
        return self._service.execute_research(query)

    def invoke(self, request: Request) -> Response:
        logger.info("Research request received (id=%s)", request.request_id)

        question = request.payload.get("question") or request.payload.get(
            "prompt"
        )

        if not question or not str(question).strip():
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error="Missing required field: 'question' or 'prompt'",
            )

        question_str = str(question).strip()
        session_id = request.payload.get("session_id")

        # --- S10: Resolve continuity ---
        context = None
        if session_id:
            context = self._context_store.get(str(session_id))

        intent, focus_topic = self._resolver.resolve(question_str, context)
        query = self._resolver.refine_query(
            question_str, intent, focus_topic, context
        )

        # --- S10: Handle PROVENANCE intent (no re-search) ---
        if intent == ContinuationIntent.PROVENANCE and context is not None:
            return self._provenance_response(request, context)

        try:
            result = self.perform_research(query)

            # --- S10: Update session context ---
            active_session_id = self._update_session(
                session_id, intent, query, result, focus_topic
            )

            if (
                request.payload.get("save_to_memory", False)
                and self._memory is not None
            ):
                self._persist_selected_findings(result)

            serialized_data = self._serialize_result(result)
            serialized_data["session_id"] = active_session_id
            serialized_data["continuation_intent"] = intent.value

            return Response(
                request_id=request.request_id,
                data=serialized_data,
                success=True,
            )
        except Exception as exc:
            logger.error("Research operation failed: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Research failure: {exc!s}",
            )

    # ------------------------------------------------------------------
    # S10: Session management
    # ------------------------------------------------------------------

    def _update_session(
        self,
        session_id: str | None,
        intent: ContinuationIntent,
        query: ResearchQuery,
        result: ResearchResult,
        focus_topic: str | None,
    ) -> str:
        """Create or update the research session context."""
        findings = tuple(f.statement for f in result.findings[:5])
        source_ids = tuple(s.source_id for s in result.sources)
        open_q = result.open_questions[:5] if result.open_questions else ()

        existing = self._context_store.get(session_id) if session_id else None

        if existing is not None:
            new_depth = existing.depth_level + (
                1 if intent == ContinuationIntent.DEEPEN else 0
            )
            self._context_store.update(
                existing.session_id,
                current_subtopic=focus_topic or query.scope,
                depth_level=new_depth,
                depth=query.depth,
                recent_findings=findings,
                source_ids=source_ids,
                open_questions=open_q,
                history_queries=existing.history_queries + (query.question,),
            )
            return existing.session_id
        else:
            ctx = self._context_store.create(query.question)
            self._context_store.update(
                ctx.session_id,
                current_subtopic=focus_topic or query.scope,
                depth=query.depth,
                recent_findings=findings,
                source_ids=source_ids,
                open_questions=open_q,
            )
            return ctx.session_id

    def _provenance_response(
        self, request: Request, context: ResearchSessionContext
    ) -> Response:
        """Return provenance from active session without re-searching."""
        reply = (
            f"From the ongoing investigation on '{context.root_query}', "
            f"I have {len(context.source_ids)} sources and "
            f"{len(context.recent_findings)} key findings so far."
        )
        return Response(
            request_id=request.request_id,
            data={
                "reply": reply,
                "session_id": context.session_id,
                "continuation_intent": "provenance",
                "source_ids": list(context.source_ids),
                "findings": list(context.recent_findings),
            },
            success=True,
        )

    # ------------------------------------------------------------------
    # Helpers (preserved from S9)
    # ------------------------------------------------------------------

    def _persist_selected_findings(self, result: ResearchResult) -> None:
        if self._memory is None:
            return
        for finding in result.findings:
            key = f"research_{uuid.uuid4().hex[:8]}"
            record = MemoryRecord(
                key=key,
                value=finding.statement,
                tags=["research", "finding", result.query.question[:30]],
                metadata={
                    "type": "research_finding",
                    "support": finding.support.value,
                    "evidence_count": len(finding.evidence_ids),
                },
            )
            try:
                self._memory.store(record)
                logger.info("Persisted research finding to memory: %s", key)
            except Exception as exc:
                logger.warning(
                    "Failed to store research finding (non-fatal): %s", exc,
                )

    @classmethod
    def _build_summary_reply(cls, result: ResearchResult) -> str:
        if result.findings:
            statements = [f.statement for f in result.findings[:2]]
            summary = " ".join(statements)
            if result.conflicts:
                conflict_note = result.conflicts[0].statement
                summary += f" Note: Conflicting findings regarding {conflict_note}"
            return summary
        if result.uncertainties:
            return f"Research found preliminary evidence: {result.uncertainties[0].statement}"
        num_sources = len(result.sources)
        return f"Completed research on '{result.query.question}' with {num_sources} sources."

    @classmethod
    def _serialize_result(cls, result: ResearchResult) -> dict[str, Any]:
        return {
            "reply": cls._build_summary_reply(result),
            "query": {
                "question": result.query.question,
                "scope": result.query.scope,
                "max_sources": result.query.max_sources,
                "depth": result.query.depth,
            },
            "sources": [
                {
                    "source_id": s.source_id,
                    "url": s.url,
                    "canonical_url": s.canonical_url,
                    "title": s.title,
                    "source_type": s.source_type.value,
                    "publisher": s.publisher,
                    "status": s.status.value,
                    "error": s.error,
                }
                for s in result.sources
            ],
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "source_id": e.source_id,
                    "claim": e.claim,
                    "excerpt": e.excerpt,
                    "relevance": e.relevance,
                }
                for e in result.evidence
            ],
            "findings": [
                {
                    "statement": f.statement,
                    "evidence_ids": list(f.evidence_ids),
                    "support": f.support.value,
                    "notes": f.notes,
                }
                for f in result.findings
            ],
            "conflicts": [
                {
                    "statement": c.statement,
                    "evidence_ids": list(c.evidence_ids),
                    "support": c.support.value,
                    "notes": c.notes,
                }
                for c in result.conflicts
            ],
            "uncertainties": [
                {
                    "statement": u.statement,
                    "evidence_ids": list(u.evidence_ids),
                    "support": u.support.value,
                    "notes": u.notes,
                }
                for u in result.uncertainties
            ],
            "open_questions": list(result.open_questions),
            "metadata": result.metadata,
        }
