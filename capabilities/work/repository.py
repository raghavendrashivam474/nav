"""Abstract storage boundary for Work persistence — S17.

Follows the same pattern as capabilities/research/investigation/repository.py
and capabilities/memory/repository.py.
"""

from abc import ABC, abstractmethod

from core.contracts.work import Work, WorkQuery


class WorkRepository(ABC):
    """Storage-agnostic persistence interface for Work items."""

    @abstractmethod
    def initialize(self) -> None:
        """Create schema / open connection. Must be idempotent."""
        pass

    @abstractmethod
    def save(self, work: Work) -> bool:
        """Insert a new Work item. Returns False on duplicate id."""
        pass

    @abstractmethod
    def get(self, work_id: str) -> Work | None:
        """Return a single Work item by id, or None if not found."""
        pass

    @abstractmethod
    def find(self, query: WorkQuery) -> list[Work]:
        """Return Work items matching query, newest first."""
        pass

    @abstractmethod
    def update(self, work: Work) -> bool:
        """Overwrite an existing Work item. False if not found."""
        pass

    @abstractmethod
    def delete(self, work_id: str) -> bool:
        """Remove a Work item. True if something was deleted."""
        pass
