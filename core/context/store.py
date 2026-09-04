"""In-memory context store — S12.

Provides simple dict-based storage for user, session, conversation,
and personal context.  No external dependencies.  Persistence beyond
process lifetime is deferred to S13/S14.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from core.contracts.context import (
    Commitment,
    ConversationContext,
    CurrentFocus,
    Goal,
    PersonalContext,
    Project,
    SessionContext,
    UserContext,
)


class ContextStore:
    """Minimal in-memory store for all context state."""

    def __init__(self) -> None:
        self._users: dict[str, UserContext] = {}
        self._sessions: dict[str, SessionContext] = {}
        self._conversations: dict[str, ConversationContext] = {}
        self._personal: dict[str, PersonalContext] = {}  # keyed by user_id

    # --- User -----------------------------------------------------------

    def get_user(self, user_id: str) -> UserContext:
        if user_id not in self._users:
            self._users[user_id] = UserContext(user_id=user_id)
        return self._users[user_id]

    def update_user(self, user_id: str, **preferences: Any) -> UserContext:
        current = self.get_user(user_id)
        merged = {**current.preferences, **preferences}
        updated = UserContext(user_id=user_id, preferences=merged)
        self._users[user_id] = updated
        return updated

    # --- Session --------------------------------------------------------

    def get_session(self, session_id: str) -> SessionContext:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext(session_id=session_id)
        return self._sessions[session_id]

    def update_session(self, session_id: str, **metadata: Any) -> SessionContext:
        current = self.get_session(session_id)
        merged = {**current.metadata, **metadata}
        updated = SessionContext(session_id=session_id, metadata=merged)
        self._sessions[session_id] = updated
        return updated

    # --- Conversation ---------------------------------------------------

    def get_conversation(self, conversation_id: str) -> ConversationContext:
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
            )
        return self._conversations[conversation_id]

    def update_conversation(
        self,
        conversation_id: str,
        turns_increment: int = 1,
        history_summary: str | None = None,
    ) -> ConversationContext:
        current = self.get_conversation(conversation_id)
        updated = ConversationContext(
            conversation_id=conversation_id,
            turns_count=current.turns_count + turns_increment,
            history_summary=history_summary or current.history_summary,
        )
        self._conversations[conversation_id] = updated
        return updated

    # --- Personal Context -----------------------------------------------

    def get_personal(self, user_id: str) -> PersonalContext:
        if user_id not in self._personal:
            self._personal[user_id] = PersonalContext()
        return self._personal[user_id]

    def set_personal(self, user_id: str, personal: PersonalContext) -> PersonalContext:
        self._personal[user_id] = personal
        return personal

    def add_project(self, user_id: str, project: Project) -> PersonalContext:
        pc = self.get_personal(user_id)
        filtered = tuple(p for p in pc.projects if p.project_id != project.project_id)
        return self.set_personal(user_id, replace(pc, projects=filtered + (project,)))

    def remove_project(self, user_id: str, project_id: str) -> PersonalContext:
        pc = self.get_personal(user_id)
        filtered = tuple(p for p in pc.projects if p.project_id != project_id)
        return self.set_personal(user_id, replace(pc, projects=filtered))

    def add_goal(self, user_id: str, goal: Goal) -> PersonalContext:
        pc = self.get_personal(user_id)
        filtered = tuple(g for g in pc.goals if g.goal_id != goal.goal_id)
        return self.set_personal(user_id, replace(pc, goals=filtered + (goal,)))

    def remove_goal(self, user_id: str, goal_id: str) -> PersonalContext:
        pc = self.get_personal(user_id)
        filtered = tuple(g for g in pc.goals if g.goal_id != goal_id)
        return self.set_personal(user_id, replace(pc, goals=filtered))

    def add_commitment(self, user_id: str, commitment: Commitment) -> PersonalContext:
        pc = self.get_personal(user_id)
        filtered = tuple(c for c in pc.commitments if c.commitment_id != commitment.commitment_id)
        return self.set_personal(user_id, replace(pc, commitments=filtered + (commitment,)))

    def remove_commitment(self, user_id: str, commitment_id: str) -> PersonalContext:
        pc = self.get_personal(user_id)
        filtered = tuple(c for c in pc.commitments if c.commitment_id != commitment_id)
        return self.set_personal(user_id, replace(pc, commitments=filtered))

    def set_focus(self, user_id: str, focus: CurrentFocus | None) -> PersonalContext:
        pc = self.get_personal(user_id)
        return self.set_personal(user_id, replace(pc, current_focus=focus))
