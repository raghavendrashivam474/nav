"""Memory service layer.

Sits between the Capability interface and the storage Repository.
Owns persistence-decision logic (what deserves to be remembered).
"""

from __future__ import annotations

import re

from capabilities.memory.repository import MemoryRepository
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
        ok = self._repo.save(record)
        if ok:
            logger.info("Memory stored: %s", record.key)
        return ok

    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        results = self._repo.find(query)
        logger.debug("Memory retrieve returned %d result(s)", len(results))
        return results

    def update(self, record: MemoryRecord) -> bool:
        ok = self._repo.replace(record)
        if ok:
            logger.info("Memory updated: %s", record.key)
        return ok

    def forget(self, key: str) -> bool:
        ok = self._repo.delete(key)
        if ok:
            logger.info("Memory forgotten: %s", key)
        return ok

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
            r"\bforget\s+(?:that|this|everything\s+about)?\s*", "", text, flags=re.IGNORECASE
        )
        return cleaned.strip().rstrip("?!.")
