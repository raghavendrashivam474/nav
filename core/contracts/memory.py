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


class MemoryCapabilityInterface(ABC):
    """Contract for persistent memory operations.

    S6 extension: added `update` and `forget` to support the full
    memory lifecycle required by the sprint Definition of Done.
    The original `store` / `retrieve` signatures are unchanged.
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
