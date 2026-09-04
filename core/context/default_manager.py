"""Default ContextManager implementation — S12.

Concrete implementation of the ContextManager contract using an
in-memory ContextStore.  Personal-context management is provided as
concrete methods beyond the abstract contract so that the S11 ABC
remains unchanged.
"""

from __future__ import annotations

from typing import Any

from core.context.context_manager import ContextManager
from core.context.store import ContextStore
from core.contracts.context import (
    Commitment,
    ConversationContext,
    CurrentFocus,
    Goal,
    NavContext,
    PersonalContext,
    Project,
    SessionContext,
    UserContext,
)


class DefaultContextManager(ContextManager):
    """In-memory ContextManager for NAV v1.2."""

    def __init__(self, store: ContextStore | None = None) -> None:
        self._store = store or ContextStore()

    @property
    def store(self) -> ContextStore:
        """Expose the underlying store for advanced use cases."""
        return self._store

    # --- ABC contract methods -------------------------------------------

    def get_context(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> NavContext:
        uid = user_id or "default"
        return NavContext(
            user=self._store.get_user(uid),
            session=self._store.get_session(session_id or "default"),
            conversation=self._store.get_conversation(conversation_id or "default"),
            personal_context=self._store.get_personal(uid),
        )

    def update_user_context(self, user_id: str, **preferences: Any) -> UserContext:
        return self._store.update_user(user_id, **preferences)

    def update_session_context(self, session_id: str, **metadata: Any) -> SessionContext:
        return self._store.update_session(session_id, **metadata)

    def update_conversation_context(
        self,
        conversation_id: str,
        turns_increment: int = 1,
        history_summary: str | None = None,
    ) -> ConversationContext:
        return self._store.update_conversation(conversation_id, turns_increment, history_summary)

    # --- Personal context (concrete, beyond ABC) ------------------------

    def add_project(self, user_id: str, project: Project) -> PersonalContext:
        """Register or update a project for the user."""
        return self._store.add_project(user_id, project)

    def remove_project(self, user_id: str, project_id: str) -> PersonalContext:
        return self._store.remove_project(user_id, project_id)

    def add_goal(self, user_id: str, goal: Goal) -> PersonalContext:
        """Register or update a goal for the user."""
        return self._store.add_goal(user_id, goal)

    def remove_goal(self, user_id: str, goal_id: str) -> PersonalContext:
        return self._store.remove_goal(user_id, goal_id)

    def add_commitment(self, user_id: str, commitment: Commitment) -> PersonalContext:
        """Register or update a commitment for the user."""
        return self._store.add_commitment(user_id, commitment)

    def remove_commitment(self, user_id: str, commitment_id: str) -> PersonalContext:
        return self._store.remove_commitment(user_id, commitment_id)

    def set_focus(self, user_id: str, focus: CurrentFocus | None) -> PersonalContext:
        """Set or clear the user's current focus."""
        return self._store.set_focus(user_id, focus)
