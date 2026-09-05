"""Abstract storage boundary for investigation persistence — S15.

Follows the same pattern as capabilities/memory/repository.py.
Swap backends by implementing this ABC.
"""

from abc import ABC, abstractmethod

from capabilities.research.investigation.models import (
    Investigation,
    InvestigationQuery,
)


class InvestigationRepository(ABC):
    """Storage-agnostic persistence interface for investigations."""

    @abstractmethod
    def initialize(self) -> None:
        """Create schema / open connection.  Must be idempotent."""
        pass

    @abstractmethod
    def save(self, investigation: Investigation) -> bool:
        """Insert a new investigation.  Returns False on duplicate id."""
        pass

    @abstractmethod
    def get(self, investigation_id: str) -> Investigation | None:
        """Return a single investigation by id, or None if not found."""
        pass

    @abstractmethod
    def find(self, query: InvestigationQuery) -> list[Investigation]:
        """Return investigations matching *query*, newest first."""
        pass

    @abstractmethod
    def update(self, investigation: Investigation) -> bool:
        """Overwrite an existing investigation.  False if not found."""
        pass

    @abstractmethod
    def delete(self, investigation_id: str) -> bool:
        """Remove an investigation.  True if something was deleted."""
        pass
