"""Research capability — registered in the CapabilityRegistry.

Implements both the generic Capability contract (for Orchestrator
routing) and ResearchCapabilityInterface (for programmatic use).

S8: Added progress reporter support and version bump.
S9: Added spoken/text summary reply generation for voice and orchestrator consumers.
"""

from __future__ import annotations

import uuid
from typing import Any

from capabilities.research.progress import ProgressReporter
from capabilities.research.service import ResearchService
from core.contracts.ai import AIGateway
from core.contracts.capability import Capability, Request, Response
from core.contracts.memory import MemoryCapabilityInterface, MemoryRecord
from core.contracts.research import (
    ResearchCapabilityInterface,
    ResearchQuery,
    ResearchResult,
    SearchProvider,
    SourceRetriever,
)
from core.log import get_logger

logger = get_logger(__name__)


class ResearchCapability(Capability, ResearchCapabilityInterface):
    """Systematic research, source exploration, and evidence synthesis for NAV."""

    def __init__(
        self,
        service: ResearchService | None = None,
        gateway: AIGateway | None = None,
        search_provider: SearchProvider | None = None,
        retriever: SourceRetriever | None = None,
        memory: MemoryCapabilityInterface | None = None,
        progress_reporter: ProgressReporter | None = None,
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

    # ------------------------------------------------------------------
    # Capability contract metadata
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "research"

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return (
            "Systematic topic exploration, evidence collection, "
            "and research map synthesis."
        )

    # ------------------------------------------------------------------
    # ResearchCapabilityInterface implementation
    # ------------------------------------------------------------------

    def perform_research(self, query: ResearchQuery) -> ResearchResult:
        return self._service.execute_research(query)

    # ------------------------------------------------------------------
    # Orchestrator-facing invoke
    # ------------------------------------------------------------------

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

        max_sources = int(request.payload.get("max_sources", 8))
        timeout_seconds = float(
            request.payload.get("timeout_seconds", 15.0)
        )
        depth = str(request.payload.get("depth", "standard"))
        scope = request.payload.get("scope")

        query = ResearchQuery(
            question=str(question).strip(),
            scope=scope,
            max_sources=max_sources,
            timeout_seconds=timeout_seconds,
            depth=depth,
        )

        try:
            result = self.perform_research(query)

            if (
                request.payload.get("save_to_memory", False)
                and self._memory is not None
            ):
                self._persist_selected_findings(result)

            serialized_data = self._serialize_result(result)

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
    # Helpers
    # ------------------------------------------------------------------

    def _persist_selected_findings(self, result: ResearchResult) -> None:
        """Saves high-confidence supported findings to persistent memory."""
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
                logger.info(
                    "Persisted research finding to memory: %s", key
                )
            except Exception as exc:
                logger.warning(
                    "Failed to store research finding to memory (non-fatal): %s",
                    exc,
                )

    @classmethod
    def _build_summary_reply(cls, result: ResearchResult) -> str:
        """Generate a concise spoken/readable summary for voice and text interfaces."""
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
        """Convert the structured research map into an API-serializable dictionary."""
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
