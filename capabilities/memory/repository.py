"""Abstract storage boundary for memory persistence.

The Core and Service layers depend on this interface, never on SQLite
directly.  Swap in a different backend by implementing this ABC.
"""

from abc import ABC, abstractmethod

from core.contracts.memory import MemoryQuery, MemoryRecord


class MemoryRepository(ABC):
    """Storage-agnostic persistence interface."""

    @abstractmethod
    def initialize(self) -> None:
        """Create schema / open connection.  Must be idempotent."""
        pass

    @abstractmethod
    def save(self, record: MemoryRecord) -> bool:
        """Insert a new record.  Returns False if the key already exists."""
        pass

    @abstractmethod
    def find(self, query: MemoryQuery) -> list[MemoryRecord]:
        """Return records matching *query*, ordered by relevance/recency."""
        pass

    @abstractmethod
    def replace(self, record: MemoryRecord) -> bool:
        """Overwrite an existing record.  Returns False if key not found."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove a record by key.  Returns True if something was deleted."""
        pass
