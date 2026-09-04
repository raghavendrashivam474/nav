"""Synthesis layer — S7 + S8.

Performs high-level synthesis of extracted evidence points, mapping them to
categorical findings, identifying contradictions, and highlighting uncertainties.

S8: Prompt-injection hardening via explicit untrusted-content delimiters.
"""

from __future__ import annotations

import json
import re

from capabilities.research.security import (
    build_safe_synthesis_prompt,
    validate_ai_output,
)
from core.contracts.ai import AIGateway, AIMessage, AIRequest
from core.contracts.research import (
    ResearchEvidence,
    ResearchFinding,
    ResearchQuery,
    ResearchResult,
    ResearchSource,
    SupportState,
)
from core.log import get_logger

logger = get_logger(__name__)


class EvidenceSynthesizer:
    """Synthesizes raw evidence arrays into categorized findings with full provenance maps."""

    def __init__(self, gateway: AIGateway) -> None:
        self.gateway = gateway

    def synthesize(
        self,
        query: ResearchQuery,
        sources: tuple[ResearchSource, ...],
        evidence: tuple[ResearchEvidence, ...],
    ) -> ResearchResult:
        logger.info(
            "Synthesizing %d evidence points from %d sources",
            len(evidence),
            len(sources),
        )

        if not evidence:
            return ResearchResult(
                query=query,
                sources=sources,
                evidence=evidence,
                findings=(),
                conflicts=(),
                uncertainties=(
                    ResearchFinding(
                        statement="No relevant evidence could be retrieved or extracted.",
                        evidence_ids=(),
                        support=SupportState.UNKNOWN,
                    ),
                ),
                open_questions=("Why did the source retrieval fail or produce empty content?",),
            )

        ev_lines = [f"ID: {ev.evidence_id} | Claim: {ev.claim}" for ev in evidence]
        ev_block = "\n".join(ev_lines)

        prompt = build_safe_synthesis_prompt(query.question, ev_block)

        ai_request = AIRequest(
            messages=[AIMessage(role="user", content=prompt)],
            temperature=0.3,
            options={
                "routing": {
                    "task_type": "research_synthesis",
                    "complexity": "high",
                    "quality": "high",
                    "privacy": "normal",
                }
            },
        )

        try:
            ai_response = self.gateway.generate(ai_request)

            # S8: Validate AI output for injection leakage
            is_safe, reason = validate_ai_output(ai_response.content)
            if not is_safe:
                logger.warning("Synthesis output flagged: %s. Using fallback.", reason)
                return self._fallback_synthesis(query, sources, evidence)

            return self._parse_synthesis(query, sources, evidence, ai_response.content)
        except Exception as exc:
            logger.error("AI synthesis failed: %s", exc)
            return self._fallback_synthesis(query, sources, evidence)

    @staticmethod
    def _build_prompt(question: str, evidence: tuple[ResearchEvidence, ...]) -> str:
        """Legacy prompt builder — kept for backward compatibility in tests."""
        ev_lines = [f"ID: {ev.evidence_id} | Claim: {ev.claim}" for ev in evidence]
        ev_block = "\n".join(ev_lines)
        return build_safe_synthesis_prompt(question, ev_block)

    def _parse_synthesis(
        self,
        query: ResearchQuery,
        sources: tuple[ResearchSource, ...],
        evidence: tuple[ResearchEvidence, ...],
        raw_content: str,
    ) -> ResearchResult:
        cleaned = raw_content.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)

            findings = [
                ResearchFinding(
                    statement=str(item["statement"]),
                    evidence_ids=tuple(str(eid) for eid in item.get("evidence_ids", [])),
                    support=SupportState.SUPPORTED,
                    notes=item.get("notes"),
                )
                for item in data.get("supported_findings", [])
            ]

            conflicts = [
                ResearchFinding(
                    statement=str(item["statement"]),
                    evidence_ids=tuple(str(eid) for eid in item.get("evidence_ids", [])),
                    support=SupportState.CONFLICTING,
                    notes=item.get("notes"),
                )
                for item in data.get("conflicting_evidence", [])
            ]

            uncertainties = [
                ResearchFinding(
                    statement=str(item["statement"]),
                    evidence_ids=tuple(str(eid) for eid in item.get("evidence_ids", [])),
                    support=SupportState.INSUFFICIENT,
                    notes=item.get("notes"),
                )
                for item in data.get("uncertainties", [])
            ]

            open_questions = tuple(str(q) for q in data.get("open_questions", []))

            return ResearchResult(
                query=query,
                sources=sources,
                evidence=evidence,
                findings=tuple(findings),
                conflicts=tuple(conflicts),
                uncertainties=tuple(uncertainties),
                open_questions=open_questions,
            )

        except Exception as exc:
            logger.warning(
                "Failed to parse synthesis JSON: %s. Rolling back to fallback.",
                exc,
            )
            return self._fallback_synthesis(query, sources, evidence)

    @staticmethod
    def _fallback_synthesis(
        query: ResearchQuery,
        sources: tuple[ResearchSource, ...],
        evidence: tuple[ResearchEvidence, ...],
    ) -> ResearchResult:
        uncertainties = [
            ResearchFinding(
                statement=f"Evidence suggests: {ev.claim}",
                evidence_ids=(ev.evidence_id,),
                support=SupportState.INSUFFICIENT,
                notes=f"Heuristic extraction from source ID {ev.source_id}",
            )
            for ev in evidence
        ]

        open_questions = (
            f"Are there more comprehensive resources detailing: '{query.question}'?",
            "What do peer-reviewed quantitative studies report regarding these initial assertions?",
        )

        return ResearchResult(
            query=query,
            sources=sources,
            evidence=evidence,
            findings=(),
            conflicts=(),
            uncertainties=tuple(uncertainties),
            open_questions=open_questions,
            metadata={"synthesis_mode": "fallback_heuristic"},
        )
