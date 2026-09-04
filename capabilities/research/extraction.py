"""Extraction layer — S7 + S8.

Uses the S5 AIGateway/ModelRouter to analyze retrieved source content
and extract structured pieces of evidence with clean provenance.

S8: Prompt-injection hardening via explicit untrusted-content delimiters.
"""

from __future__ import annotations

import json
import re
import uuid

from capabilities.research.security import (
    build_safe_extraction_prompt,
    validate_ai_output,
)
from core.contracts.ai import AIGateway, AIMessage, AIRequest
from core.contracts.research import (
    ResearchEvidence,
    ResearchQuery,
    RetrievedContent,
)
from core.log import get_logger

logger = get_logger(__name__)


class EvidenceExtractor:
    """Uses the AI Gateway to extract relevant claims from raw content."""

    def __init__(self, gateway: AIGateway) -> None:
        self.gateway = gateway

    def extract(
        self, query: ResearchQuery, content: RetrievedContent
    ) -> list[ResearchEvidence]:
        """Analyzes content and extracts evidence points matching the research question."""
        logger.info("Extracting evidence from source %s", content.source_id)

        prompt = build_safe_extraction_prompt(query.question, content.text)

        ai_request = AIRequest(
            messages=[AIMessage(role="user", content=prompt)],
            temperature=0.2,
            options={
                "routing": {
                    "task_type": "research_extraction",
                    "complexity": "standard",
                    "quality": "standard",
                    "privacy": "normal",
                }
            },
        )

        try:
            ai_response = self.gateway.generate(ai_request)

            # S8: Validate AI output for injection leakage
            is_safe, reason = validate_ai_output(ai_response.content)
            if not is_safe:
                logger.warning(
                    "AI output flagged for source %s: %s. Using fallback.",
                    content.source_id,
                    reason,
                )
                return self._fallback_extraction(
                    content.source_id, content.text, query.question
                )

            return self._parse_response(content.source_id, ai_response.content)
        except Exception as exc:
            logger.error(
                "AI extraction failed for %s: %s", content.source_id, exc
            )
            return self._fallback_extraction(
                content.source_id, content.text, query.question
            )

    @staticmethod
    def _build_prompt(question: str, text: str) -> str:
        """Legacy prompt builder — kept for backward compatibility in tests."""
        return build_safe_extraction_prompt(question, text)

    def _parse_response(
        self, source_id: str, raw_content: str
    ) -> list[ResearchEvidence]:
        """Parse AI output with extreme robustness against markdown wrap or partial outputs."""
        cleaned = raw_content.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            items = json.loads(cleaned)
            if not isinstance(items, list):
                raise ValueError("AI response did not return a list")

            evidence_points = []
            for item in items:
                if not isinstance(item, dict) or "claim" not in item:
                    continue

                evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
                evidence_points.append(
                    ResearchEvidence(
                        evidence_id=evidence_id,
                        source_id=source_id,
                        claim=str(item["claim"]).strip(),
                        excerpt=str(item.get("excerpt", "")).strip(),
                        relevance=str(
                            item.get("relevance", "medium")
                        ).lower(),
                    )
                )
            return evidence_points

        except Exception as exc:
            logger.warning(
                "Failed to parse AI extraction JSON: %s. Using fallback parser.",
                exc,
            )
            return self._fallback_heuristic_parse(source_id, cleaned)

    def _fallback_heuristic_parse(
        self, source_id: str, text: str
    ) -> list[ResearchEvidence]:
        """Parse non-JSON line-by-line responses to avoid failing the research query."""
        evidence_points = []
        lines = text.split("\n")

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            prefixes = ("here is", "here are", "i found", "notes")
            if trimmed.endswith(":") or trimmed.lower().startswith(prefixes):
                continue

            clean_line = trimmed.lstrip("-*\u20221234567890. ")
            if len(clean_line) < 15:
                continue

            evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
            evidence_points.append(
                ResearchEvidence(
                    evidence_id=evidence_id,
                    source_id=source_id,
                    claim=clean_line,
                    excerpt="",
                    relevance="medium",
                )
            )

        return evidence_points

    @staticmethod
    def _fallback_extraction(
        source_id: str, text: str, question: str
    ) -> list[ResearchEvidence]:
        """Completely offline fallback parser."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        evidence_points = []

        count = 0
        for s in sentences:
            s = s.strip()
            if len(s) > 20 and count < 3:
                evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
                evidence_points.append(
                    ResearchEvidence(
                        evidence_id=evidence_id,
                        source_id=source_id,
                        claim=s,
                        excerpt=s,
                        relevance="medium",
                    )
                )
                count += 1

        return evidence_points
