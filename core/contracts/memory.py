"""Memory contracts — S6 + S13.

S6: MemoryRecord, MemoryQuery, MemoryCapabilityInterface.
S13: Added optional intelligent-retrieval filters to MemoryQuery.
     All new fields default to None, preserving full backward
     compatibility with every existing MemoryQuery construction site.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryRecord:
    key: str
    value: Any
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryQuery:
    query_text: str | None = None
    tags: list[str] = field(default_factory=list)
    limit: int = 10
    # S13: intelligent retrieval filters (all optional)
    memory_type: str | None = None
    min_importance: str | None = None
    confidence: str | None = None
    lifecycle_status: str | None = None


class MemoryCapabilityInterface(ABC):
    """Contract for persistent memory operations.

    S6: store / retrieve / update / forget.
    S13: store() auto-applies semantic defaults via the service layer.
         New lifecycle methods (supersede, detect_contradictions) live
         on MemoryService, not on this ABC, to avoid breaking changes.
    """

    @abstractmethod
    def store(self, record: MemoryRecord) -> bool:
        """Persist a new memory record. Returns False on duplicate key."""
        pass

    @abstractmethod
    def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Retrieve memories matching the query."""
        pass

    @abstractmethod
    def update(self, record: MemoryRecord) -> bool:
        """Update an existing memory (matched by key). Returns False if not found."""
        pass

    @abstractmethod
    def forget(self, key: str) -> bool:
        """Delete a memory by key. Returns True if a record was removed."""
        pass
