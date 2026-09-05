"""Memory service layer.

Sits between the Capability interface and the storage Repository.
Owns persistence-decision logic (what deserves to be remembered).

S13: Added semantic defaults on store(), supersede() for lifecycle
management, and detect_contradictions() for conflict awareness.
"""

from __future__ import annotations

import re

from capabilities.memory.repository import MemoryRepository
from capabilities.memory.semantics import (
    DEFAULT_TYPE,
    META_LIFECYCLE,
    META_SUPERSEDED_BY,
    META_SUPERSEDES,
    META_TYPE,
    LifecycleStatus,
    apply_defaults,
)
from core.contracts.memory import MemoryCapabilityInterface, MemoryQuery, MemoryRecord
from core.log import get_logger

logger = get_logger(__name__)


class MemoryService(MemoryCapabilityInterface):
    """High-level memory operations backed by a replaceable repository."""

    def __init__(self, repository: MemoryRepository) -> None:
        self._repo = repository
        self._repo.initialize()

    # ------------------------------------------------------------------
    # MemoryCapabilityInterface
    # ------------------------------------------------------------------

    def store(self, record: MemoryRecord) -> bool:
        # S13: auto-apply semantic defaults to metadata
        enriched_meta = apply_defaults(record.metadata)
        enriched = MemoryRecord(
            key=record.key,
            value=record.value,
            tags=record.tags,
            metadata=enriched_meta,
        )
        ok = self._repo.save(enriched)
        if ok:
            logger.info(
                "Memory stored: %s [type=%s importance=%s confidence=%s]",
                enriched.key,
                enriched_meta.get("memory_type"),
                enriched_meta.get("importance"),
                enriched_meta.get("confidence"),
            )
        return ok

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        results = self._repo.find(query)
        logger.debug("Memory retrieve returned %d result(s)", len(results))
        return results

    def update(self, record: MemoryRecord) -> bool:
        # S13: ensure semantics are preserved on update
        enriched_meta = apply_defaults(record.metadata)
        enriched = MemoryRecord(
            key=record.key,
            value=record.value,
            tags=record.tags,
            metadata=enriched_meta,
        )
        ok = self._repo.replace(enriched)
        if ok:
            logger.info("Memory updated: %s", enriched.key)
        return ok

    def forget(self, key: str) -> bool:
        ok = self._repo.delete(key)
        if ok:
            logger.info("Memory forgotten: %s", key)
        return ok

    # ------------------------------------------------------------------
    # S13: Lifecycle — Supersede
    # ------------------------------------------------------------------

    def supersede(self, old_key: str, new_record: MemoryRecord) -> bool:
        """Replace an existing memory with a new version.

        The old memory is marked SUPERSEDED (not deleted) and linked
        to the new record.  The new record carries a back-link to the
        old one.  This preserves decision evolution history.

        Returns True only if both the old update and new insert succeed.
        """
        old = self._repo.get(old_key)
        if old is None:
            logger.warning("Cannot supersede: key %s not found", old_key)
            return False

        # Mark old as superseded
        old_meta = dict(old.metadata)
        old_meta[META_LIFECYCLE] = LifecycleStatus.SUPERSEDED.value
        old_meta[META_SUPERSEDED_BY] = new_record.key
        marked_old = MemoryRecord(
            key=old.key, value=old.value, tags=old.tags, metadata=old_meta
        )
        if not self._repo.replace(marked_old):
            return False

        # Enrich and store new record with back-link
        new_meta = apply_defaults(new_record.metadata)
        new_meta[META_SUPERSEDES] = old_key
        enriched_new = MemoryRecord(
            key=new_record.key,
            value=new_record.value,
            tags=new_record.tags,
            metadata=new_meta,
        )
        ok = self._repo.save(enriched_new)
        if ok:
            logger.info("Memory superseded: %s → %s", old_key, new_record.key)
        return ok

    # ------------------------------------------------------------------
    # S13: Contradiction Detection
    # ------------------------------------------------------------------

    def detect_contradictions(self, record: MemoryRecord) -> list[MemoryRecord]:
        """Find active memories that potentially contradict *record*.

        A potential contradiction exists when two memories share the
        same type AND have overlapping tags AND carry different values.

        This method flags but does NOT auto-resolve.  Resolution is a
        higher-layer concern (S14+).
        """
        mem_type = record.metadata.get(META_TYPE, DEFAULT_TYPE)
        candidates = self._repo.find(
            MemoryQuery(
                memory_type=mem_type,
                lifecycle_status=LifecycleStatus.ACTIVE.value,
                limit=100,
            )
        )
        record_tags = set(record.tags)
        contradictions: list[MemoryRecord] = []
        for c in candidates:
            if c.key == record.key:
                continue
            if record_tags and record_tags & set(c.tags):
                if c.value != record.value:
                    contradictions.append(c)
        if contradictions:
            logger.info(
                "Potential contradictions for %s: %d found",
                record.key,
                len(contradictions),
            )
        return contradictions

    # ------------------------------------------------------------------
    # Persistence-decision helpers (S6: deterministic / keyword-based)
    # ------------------------------------------------------------------

    @staticmethod
    def is_memory_request(text: str) -> bool:
        """Detect explicit user intent to store a memory."""
        patterns = [
            r"\bremember\s+(?:that\s+)?",
            r"\bsave\s+(?:this|that)\b",
            r"\bkeep\s+in\s+mind\b",
            r"\bnote\s+that\b",
        ]
        lower = text.lower()
        return any(re.search(p, lower) for p in patterns)

    @staticmethod
    def extract_memory_content(text: str) -> str:
        """Pull the memorable content out of an explicit request."""
        patterns = [
            r"\bremember\s+that\s+(.+)",
            r"\bremember\s+(.+)",
            r"\bkeep\s+in\s+mind\s+(?:that\s+)?(.+)",
            r"\bnote\s+that\s+(.+)",
            r"\bsave\s+(?:this|that)\s*[:\-]?\s*(.+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip().rstrip(".")
        return text.strip()

    @staticmethod
    def is_forget_request(text: str) -> bool:
        """Detect explicit user intent to delete a memory."""
        return bool(re.search(r"\bforget\b", text, re.IGNORECASE))

    @staticmethod
    def extract_forget_query(text: str) -> str:
        """Extract search terms from a forget request."""
        cleaned = re.sub(
            r"\bforget\s+(?:that|this|everything\s+about)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return cleaned.strip().rstrip("?!.").strip()
