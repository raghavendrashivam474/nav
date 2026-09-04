"""Research continuity - S10.

Resolves follow-up intent from user input and active research context,
enabling multi-turn research conversations without polluting long-term memory.
"""

from __future__ import annotations

import re

from core.contracts.context import ResearchSessionContext
from core.contracts.research import ContinuationIntent, ResearchQuery
from core.log import get_logger

logger = get_logger(__name__)


class ResearchContinuityResolver:
    """Classifies follow-up intent and refines queries based on context."""

    DEEPEN_PATTERNS: list[str] = [
        r"\bgo\s+deeper\b",
        r"\bdig\s+deeper\b",
        r"\bmore\s+details?\b",
        r"\btell\s+me\s+more\b",
        r"\bexpand\b",
        r"\belaborate\b",
        r"\bwhat\s+else\b",
        r"\bcontinue\b",
        r"\bdeeper\s+analysis\b",
    ]

    FOCUS_PATTERNS: list[str] = [
        r"\bfocus\s+on\s+(.+)",
        r"\bwhat\s+about\s+(.+)",
        r"\bspecifically\s+(.+)",
        r"\bnarrow\s+(?:down\s+)?to\s+(.+)",
        r"\bconcentrate\s+on\s+(.+)",
        r"\bzoom\s+in\s+on\s+(.+)",
    ]

    PROVENANCE_PATTERNS: list[str] = [
        r"\b(?:show|find|get)\s+(?:me\s+)?(?:the\s+)?(?:primary\s+)?sources?\b",
        r"\bwhere\s+did\s+you\s+find\b",
        r"\bcitations?\b",
        r"\breferences?\b",
        r"\bwhich\s+sources?\b",
        r"\bprovenance\b",
    ]

    def resolve(
        self, prompt: str, context: ResearchSessionContext | None
    ) -> tuple[ContinuationIntent, str | None]:
        """Classify intent given the active research context.

        Returns:
            (intent, focus_topic) where focus_topic is set for FOCUS intent.
        """
        if context is None:
            return ContinuationIntent.NEW, None

        prompt_lower = prompt.lower().strip()

        for pattern in self.DEEPEN_PATTERNS:
            if re.search(pattern, prompt_lower):
                logger.info("Continuity: DEEPEN intent detected")
                return ContinuationIntent.DEEPEN, None

        for pattern in self.FOCUS_PATTERNS:
            m = re.search(pattern, prompt_lower)
            if m:
                focus = m.group(1).strip().rstrip("?!.") if m.lastindex else None
                logger.info("Continuity: FOCUS intent (topic=%s)", focus)
                return ContinuationIntent.FOCUS, focus

        for pattern in self.PROVENANCE_PATTERNS:
            if re.search(pattern, prompt_lower):
                logger.info("Continuity: PROVENANCE intent detected")
                return ContinuationIntent.PROVENANCE, None

        logger.info("Continuity: NEW intent (unrelated query)")
        return ContinuationIntent.NEW, None

    def refine_query(
        self,
        original_prompt: str,
        intent: ContinuationIntent,
        focus_topic: str | None,
        context: ResearchSessionContext | None,
    ) -> ResearchQuery:
        """Construct a refined ResearchQuery based on intent and context."""
        if context is None or intent == ContinuationIntent.NEW:
            return ResearchQuery(question=original_prompt.strip())

        if intent == ContinuationIntent.DEEPEN:
            if context.open_questions:
                question = f"{context.root_query}: {context.open_questions[0]}"
            else:
                question = (
                    f"{context.root_query} - deeper analysis, "
                    "unresolved challenges, and technical limitations"
                )
            return ResearchQuery(
                question=question,
                scope=context.current_subtopic or context.root_query,
                depth="deep",
                max_sources=8,
            )

        if intent == ContinuationIntent.FOCUS:
            topic = focus_topic or original_prompt
            question = f"{context.root_query} - {topic}"
            return ResearchQuery(
                question=question,
                scope=topic,
                depth=context.depth,
                max_sources=8,
            )

        if intent == ContinuationIntent.PROVENANCE:
            return ResearchQuery(
                question=context.root_query,
                scope="provenance",
                depth="standard",
                max_sources=0,
            )

        return ResearchQuery(question=original_prompt.strip())
