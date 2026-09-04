"""Context Manager contract — S11.

Defines the abstract interface for resolving, assembling, and tracking
NavContext across user, session, and capability boundaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.contracts.context import (
    ConversationContext,
    NavContext,
    SessionContext,
    UserContext,
)


class ContextManager(ABC):
    """Contract for managing contextual snapshots in NAV."""

    @abstractmethod
    def get_context(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> NavContext:
        """Assemble an immutable NavContext snapshot for the active interaction."""
        pass

    @abstractmethod
    def update_user_context(self, user_id: str, **preferences: Any) -> UserContext:
        """Update or register preferences for a given user."""
        pass

    @abstractmethod
    def update_session_context(self, session_id: str, **metadata: Any) -> SessionContext:
        """Update metadata associated with an ongoing session."""
        pass

    @abstractmethod
    def update_conversation_context(
        self,
        conversation_id: str,
        turns_increment: int = 1,
        history_summary: str | None = None,
    ) -> ConversationContext:
        """Update conversation turns and summary state."""
        pass
