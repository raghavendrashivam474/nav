"""Memory → Context integration — S14.

Provides the bridge that allows NAV's Memory Intelligence (S13) to
inform its Context Foundation (S12) without merging the two systems.

Key principle: Memory informs Context; Memory does not become Context.

Architecture:
    - Depends only on core/contracts (MemoryCapabilityInterface, NavContext)
    - Does NOT import from capabilities/ (avoids core → capabilities dep)
    - Read-only: never writes to Memory or Context
    - Resilient: returns un-enriched snapshot on any failure
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.contracts.context import NavContext
from core.contracts.memory import MemoryCapabilityInterface, MemoryQuery, MemoryRecord
from core.log import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# S13 semantic value constants
# ---------------------------------------------------------------------------
# These are the well-known string values stored in MemoryRecord.metadata
# by the S13 semantics layer (capabilities/memory/semantics.py).
# Referenced here as literals to avoid a core → capabilities import.
# The authoritative enum definitions live in the semantics module.

_LIFECYCLE_ACTIVE = "active"
_LIFECYCLE_SUPERSEDED = "superseded"
_LIFECYCLE_ARCHIVED = "archived"

_CONFIDENCE_EXPLICIT = "explicit"
_CONFIDENCE_OBSERVED = "observed"
_CONFIDENCE_INFERRED = "inferred"

_TYPE_DECISION = "decision"
_TYPE_PREFERENCE = "preference"
_TYPE_COMMITMENT = "commitment"
_TYPE_GOAL = "goal"
_TYPE_INSTRUCTION = "instruction"

_IMPORTANCE_LOW = "low"
_IMPORTANCE_NORMAL = "normal"
_IMPORTANCE_HIGH = "high"
_IMPORTANCE_CRITICAL = "critical"

_IMPORTANCE_RANK: dict[str, int] = {
    _IMPORTANCE_LOW: 1,
    _IMPORTANCE_NORMAL: 2,
    _IMPORTANCE_HIGH: 3,
    _IMPORTANCE_CRITICAL: 4,
}


# ---------------------------------------------------------------------------
# S14 data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryContextItem:
    """A single memory selected as contextually relevant.

    Preserves full provenance back to the source MemoryRecord so that
    downstream consumers can trace, explain, and audit contextual data.
    """

    memory_key: str
    value: Any
    memory_type: str
    importance: str
    confidence: str
    provenance: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextualSnapshot:
    """Enriched context: base NavContext + relevant memories.

    This is the primary S14 output.  It wraps the existing NavContext
    (unchanged, by reference) and adds a curated set of relevant
    memories drawn from the Memory Intelligence layer.

    The separation is deliberate:
        - base_context remains the S12 NavContext (frozen, untouched)
        - relevant_memories are S13 memories filtered for relevance
        - They are combined here, not merged into one semantic object
    """

    base_context: NavContext
    relevant_memories: tuple[MemoryContextItem, ...] = ()
    interaction_hint: str = ""
    timestamp: str = ""

    @property
    def has_enrichment(self) -> bool:
        """True if any memories were selected as contextually relevant."""
        return len(self.relevant_memories) > 0


# ---------------------------------------------------------------------------
# S14 integrator
# ---------------------------------------------------------------------------


class MemoryContextIntegrator:
    """Bridge between Memory Intelligence (S13) and Context (S12).

    Queries Memory for information relevant to the current context and
    interaction, producing a ContextualSnapshot.

    This class is read-only: it never writes to Memory or Context.
    It depends only on the MemoryCapabilityInterface ABC, making it
    testable with any memory backend.

    Usage::

        integrator = MemoryContextIntegrator(memory_service)
        snapshot = integrator.build_snapshot(nav_context, "debug S14")
        if snapshot.has_enrichment:
            for mem in snapshot.relevant_memories:
                print(f"{mem.memory_type}: {mem.value}")
    """

    # Memory types most relevant for context enrichment.
    # Observations and temporary memories are deprioritized.
    _CONTEXT_RELEVANT_TYPES: frozenset[str] = frozenset(
        {
            _TYPE_PREFERENCE,
            _TYPE_DECISION,
            _TYPE_GOAL,
            _TYPE_COMMITMENT,
            _TYPE_INSTRUCTION,
        }
    )

    def __init__(self, memory: MemoryCapabilityInterface) -> None:
        self._memory = memory

    def build_snapshot(
        self,
        context: NavContext,
        interaction_hint: str = "",
        max_memories: int = 10,
    ) -> ContextualSnapshot:
        """Build an enriched ContextualSnapshot.

        Args:
            context: The current NavContext (never modified).
            interaction_hint: Optional text describing the current
                interaction, used to improve memory relevance.
            max_memories: Maximum number of memories to include.

        Returns:
            A ContextualSnapshot.  Never raises; returns an
            un-enriched snapshot if memory is unavailable or empty.
        """
        now = datetime.now(timezone.utc).isoformat()

        try:
            relevant = self._find_relevant_memories(
                context,
                interaction_hint,
                max_memories,
            )
        except Exception:
            logger.warning(
                "Memory context integration failed; returning un-enriched snapshot",
                exc_info=True,
            )
            relevant = []

        return ContextualSnapshot(
            base_context=context,
            relevant_memories=tuple(relevant),
            interaction_hint=interaction_hint,
            timestamp=now,
        )

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _find_relevant_memories(
        self,
        context: NavContext,
        interaction_hint: str,
        max_memories: int,
    ) -> list[MemoryContextItem]:
        """Full pipeline: extract → query → filter → rank → convert."""

        # 1. Extract relevance dimensions from context
        terms = self._extract_relevance_terms(context, interaction_hint)
        if not terms:
            return []

        # 2. Query memory for active candidates
        candidates = self._query_candidates(terms)
        if not candidates:
            return []

        # 3. Filter: only active lifecycle
        active = self._filter_active(candidates)
        if not active:
            return []

        # 4. Rank by S13 semantics + contextual relevance
        ranked = self._rank(active, context)

        # 5. Convert to provenance-preserving items
        return [self._to_context_item(m) for m in ranked[:max_memories]]

    def _extract_relevance_terms(
        self,
        context: NavContext,
        interaction_hint: str,
    ) -> list[str]:
        """Extract search terms from PersonalContext dimensions."""
        terms: list[str] = []

        pc = context.personal_context
        if pc is not None:
            for project in pc.projects:
                if project.name:
                    terms.append(project.name)
                if project.current_focus:
                    terms.append(project.current_focus)

            for goal in pc.goals:
                if goal.description:
                    terms.append(goal.description)

            for commitment in pc.commitments:
                if commitment.description:
                    terms.append(commitment.description)

            if pc.current_focus is not None:
                if pc.current_focus.topic:
                    terms.append(pc.current_focus.topic)
                if pc.current_focus.activity:
                    terms.append(pc.current_focus.activity)

        if interaction_hint:
            terms.append(interaction_hint)

        return terms

    def _query_candidates(self, terms: list[str]) -> list[MemoryRecord]:
        """Query memory for active candidates matching relevance terms."""
        seen_keys: set[str] = set()
        candidates: list[MemoryRecord] = []

        for term in terms:
            query = MemoryQuery(
                query_text=term,
                lifecycle_status=_LIFECYCLE_ACTIVE,
                limit=20,
            )
            results = self._memory.retrieve(query)
            for record in results:
                if record.key not in seen_keys:
                    seen_keys.add(record.key)
                    candidates.append(record)

        return candidates

    def _filter_active(
        self,
        records: list[MemoryRecord],
    ) -> list[MemoryRecord]:
        """Remove superseded and archived memories."""
        return [
            r
            for r in records
            if r.metadata.get("lifecycle_status", _LIFECYCLE_ACTIVE) == _LIFECYCLE_ACTIVE
        ]

    def _rank(
        self,
        records: list[MemoryRecord],
        context: NavContext,
    ) -> list[MemoryRecord]:
        """Rank memories by contextual relevance.

        Uses S13 semantics (importance, confidence) plus type
        relevance and tag overlap.  Kept deliberately simple.
        """

        def _score(record: MemoryRecord) -> float:
            score = 0.0
            meta = record.metadata

            # Importance weight (S13)
            importance = meta.get("importance", _IMPORTANCE_NORMAL)
            score += _IMPORTANCE_RANK.get(importance, 2) * 2.0

            # Confidence weight (S13)
            confidence = meta.get("confidence", _CONFIDENCE_EXPLICIT)
            if confidence == _CONFIDENCE_EXPLICIT:
                score += 3.0
            elif confidence == _CONFIDENCE_OBSERVED:
                score += 2.0
            elif confidence == _CONFIDENCE_INFERRED:
                score += 1.0

            # Type relevance
            mem_type = meta.get("memory_type", "fact")
            if mem_type in self._CONTEXT_RELEVANT_TYPES:
                score += 2.0

            # Tag overlap with context dimensions
            if context.personal_context is not None:
                context_terms: set[str] = set()
                for p in context.personal_context.projects:
                    if p.name:
                        context_terms.add(p.name.lower())
                focus = context.personal_context.current_focus
                if focus is not None and focus.topic:
                    context_terms.add(focus.topic.lower())

                record_tags = {t.lower() for t in record.tags}
                overlap = len(context_terms & record_tags)
                score += overlap * 1.5

            return score

        return sorted(records, key=_score, reverse=True)

    def _to_context_item(self, record: MemoryRecord) -> MemoryContextItem:
        """Convert a MemoryRecord to a MemoryContextItem.

        Preserves full provenance and all metadata for traceability.
        """
        meta = record.metadata
        return MemoryContextItem(
            memory_key=record.key,
            value=record.value,
            memory_type=meta.get("memory_type", "fact"),
            importance=meta.get("importance", _IMPORTANCE_NORMAL),
            confidence=meta.get("confidence", _CONFIDENCE_EXPLICIT),
            provenance=meta.get("provenance", ""),
            tags=list(record.tags),
            metadata=dict(meta),
        )
