"""Tests for ContextManager abstract contract."""

import unittest
from typing import Any

from core.context.context_manager import ContextManager
from core.contracts.context import (
    ConversationContext,
    NavContext,
    SessionContext,
    UserContext,
)


class StubContextManager(ContextManager):
    """Minimal concrete stub to test interface contract compliance."""

    def __init__(self) -> None:
        self.user = UserContext(user_id="u_default")
        self.session = SessionContext(session_id="s_default")
        self.conversation = ConversationContext(conversation_id="c_default")

    def get_context(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
    ) -> NavContext:
        return NavContext(
            user=self.user,
            session=self.session,
            conversation=self.conversation,
        )

    def update_user_context(self, user_id: str, **preferences: Any) -> UserContext:
        self.user = UserContext(user_id=user_id, preferences=preferences)
        return self.user

    def update_session_context(self, session_id: str, **metadata: Any) -> SessionContext:
        self.session = SessionContext(session_id=session_id, metadata=metadata)
        return self.session

    def update_conversation_context(
        self,
        conversation_id: str,
        turns_increment: int = 1,
        history_summary: str | None = None,
    ) -> ConversationContext:
        self.conversation = ConversationContext(
            conversation_id=conversation_id,
            turns_count=self.conversation.turns_count + turns_increment,
            history_summary=history_summary or self.conversation.history_summary,
        )
        return self.conversation


class TestContextManagerContract(unittest.TestCase):
    def test_stub_lifecycle(self) -> None:
        manager = StubContextManager()

        # Check default context snapshot
        ctx = manager.get_context()
        self.assertEqual(ctx.user.user_id, "u_default")
        self.assertEqual(ctx.session.session_id, "s_default")
        self.assertEqual(ctx.conversation.conversation_id, "c_default")
        self.assertEqual(ctx.conversation.turns_count, 0)

        # Update user
        u = manager.update_user_context("u_123", theme="dark", locale="en")
        self.assertEqual(u.user_id, "u_123")
        self.assertEqual(u.preferences["theme"], "dark")

        # Update session
        s = manager.update_session_context("s_456", mode="research")
        self.assertEqual(s.session_id, "s_456")
        self.assertEqual(s.metadata["mode"], "research")

        # Update conversation
        c = manager.update_conversation_context(
            "c_789", turns_increment=2, history_summary="Discussed AI"
        )
        self.assertEqual(c.conversation_id, "c_789")
        self.assertEqual(c.turns_count, 2)
        self.assertEqual(c.history_summary, "Discussed AI")

        # Verify assembled snapshot
        updated_ctx = manager.get_context()
        self.assertEqual(updated_ctx.user.user_id, "u_123")
        self.assertEqual(updated_ctx.session.session_id, "s_456")
        self.assertEqual(updated_ctx.conversation.conversation_id, "c_789")
        self.assertEqual(updated_ctx.conversation.turns_count, 2)
