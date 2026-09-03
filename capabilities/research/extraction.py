"""Extraction layer — S7.

Uses the S5 AIGateway/ModelRouter to analyze retrieved source content
and extract structured pieces of evidence with clean provenance.
"""

from __future__ import annotations

import json
import re
import uuid

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

    def extract(self, query: ResearchQuery, content: RetrievedContent) -> list[ResearchEvidence]:
        """Analyzes content and extracts evidence points matching the research question."""
        logger.info("Extracting evidence from source %s", content.source_id)

        prompt = self._build_prompt(query.question, content.text)

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
            return self._parse_response(content.source_id, ai_response.content)
        except Exception as exc:
            logger.error("AI extraction failed for %s: %s", content.source_id, exc)
            return self._fallback_extraction(content.source_id, content.text, query.question)

    @staticmethod
    def _build_prompt(question: str, text: str) -> str:
        return f"""Analyze the technical text below to identify evidence relevant to:
"{question}"

Format your output as a raw JSON array of objects. Do not write markdown code blocks.
Each object in the array must have exactly these keys:
- "claim": A clear, single-sentence technical claim or observation.
- "excerpt": A direct sentence or quote from the text that supports this claim.
- "relevance": Either "high", "medium", or "low".

Text to analyze:
---
{text}
---
JSON:"""

    def _parse_response(self, source_id: str, raw_content: str) -> list[ResearchEvidence]:
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
                        relevance=str(item.get("relevance", "medium")).lower(),
                    )
                )
            return evidence_points

        except Exception as exc:
            logger.warning("Failed to parse AI extraction JSON: %s. Using fallback parser.", exc)
            return self._fallback_heuristic_parse(source_id, cleaned)

    def _fallback_heuristic_parse(self, source_id: str, text: str) -> list[ResearchEvidence]:
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

            clean_line = trimmed.lstrip("-*•1234567890. ")
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
    def _fallback_extraction(source_id: str, text: str, question: str) -> list[ResearchEvidence]:
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
