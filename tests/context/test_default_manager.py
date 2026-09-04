"""Tests for S12 DefaultContextManager — contract compliance + personal context."""

from core.context.context_manager import ContextManager
from core.context.default_manager import DefaultContextManager
from core.contracts.context import (
    Commitment,
    CurrentFocus,
    Goal,
    NavContext,
    Project,
)


class TestContractCompliance:
    def test_is_context_manager(self) -> None:
        mgr = DefaultContextManager()
        assert isinstance(mgr, ContextManager)

    def test_get_context_returns_nav_context(self) -> None:
        mgr = DefaultContextManager()
        ctx = mgr.get_context(session_id="s1", user_id="u1", conversation_id="c1")
        assert isinstance(ctx, NavContext)
        assert ctx.user.user_id == "u1"
        assert ctx.session.session_id == "s1"
        assert ctx.conversation.conversation_id == "c1"

    def test_get_context_defaults(self) -> None:
        mgr = DefaultContextManager()
        ctx = mgr.get_context()
        assert ctx.user.user_id == "default"
        assert ctx.session.session_id == "default"

    def test_update_user_context(self) -> None:
        mgr = DefaultContextManager()
        user = mgr.update_user_context("u1", theme="dark")
        assert user.preferences["theme"] == "dark"

    def test_update_session_context(self) -> None:
        mgr = DefaultContextManager()
        session = mgr.update_session_context("s1", mode="voice")
        assert session.metadata["mode"] == "voice"

    def test_update_conversation_context(self) -> None:
        mgr = DefaultContextManager()
        conv = mgr.update_conversation_context("c1", turns_increment=3)
        assert conv.turns_count == 3


class TestPersonalContextIntegration:
    def test_snapshot_includes_personal_context(self) -> None:
        mgr = DefaultContextManager()
        mgr.add_project("u1", Project(project_id="p1", name="NAV"))
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert len(ctx.personal_context.projects) == 1

    def test_add_and_retrieve_project(self) -> None:
        mgr = DefaultContextManager()
        mgr.add_project("u1", Project(project_id="p1", name="NAV", current_focus="S12"))
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert ctx.personal_context.projects[0].current_focus == "S12"

    def test_add_goal(self) -> None:
        mgr = DefaultContextManager()
        mgr.add_goal("u1", Goal(goal_id="g1", description="Build NAV v1"))
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert ctx.personal_context.goals[0].description == "Build NAV v1"

    def test_add_commitment(self) -> None:
        mgr = DefaultContextManager()
        mgr.add_commitment("u1", Commitment(commitment_id="c1", description="Finish S12"))
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert len(ctx.personal_context.commitments) == 1

    def test_set_and_clear_focus(self) -> None:
        mgr = DefaultContextManager()
        mgr.set_focus("u1", CurrentFocus(project_id="p1", topic="context"))
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert ctx.personal_context.current_focus is not None
        assert ctx.personal_context.current_focus.topic == "context"

        mgr.set_focus("u1", None)
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert ctx.personal_context.current_focus is None

    def test_remove_project(self) -> None:
        mgr = DefaultContextManager()
        mgr.add_project("u1", Project(project_id="p1", name="NAV"))
        mgr.add_project("u1", Project(project_id="p2", name="Other"))
        mgr.remove_project("u1", "p1")
        ctx = mgr.get_context(user_id="u1")
        assert ctx.personal_context is not None
        assert len(ctx.personal_context.projects) == 1
        assert ctx.personal_context.projects[0].project_id == "p2"

    def test_full_scenario(self) -> None:
        """Simulate the S12 victory scenario from the brief."""
        mgr = DefaultContextManager()
        uid = "ragha"

        mgr.update_user_context(uid, communication="concise")
        mgr.add_project(uid, Project(project_id="nav", name="NAV", status="active"))
        mgr.add_goal(uid, Goal(goal_id="g1", description="Build NAV v1", project_id="nav"))
        mgr.add_commitment(
            uid,
            Commitment(commitment_id="c1", description="Continue NAV development"),
        )
        mgr.set_focus(
            uid,
            CurrentFocus(project_id="nav", activity="S12", topic="Context Foundation"),
        )

        ctx = mgr.get_context(user_id=uid, session_id="s1", conversation_id="c1")

        assert ctx.user.preferences["communication"] == "concise"
        assert ctx.personal_context is not None
        assert ctx.personal_context.projects[0].name == "NAV"
        assert ctx.personal_context.goals[0].description == "Build NAV v1"
        assert ctx.personal_context.commitments[0].description == "Continue NAV development"
        assert ctx.personal_context.current_focus is not None
        assert ctx.personal_context.current_focus.topic == "Context Foundation"


class TestSessionIsolation:
    def test_sessions_independent(self) -> None:
        mgr = DefaultContextManager()
        mgr.update_session_context("s1", mode="voice")
        mgr.update_session_context("s2", mode="text")

        ctx1 = mgr.get_context(session_id="s1")
        ctx2 = mgr.get_context(session_id="s2")

        assert ctx1.session.metadata["mode"] == "voice"
        assert ctx2.session.metadata["mode"] == "text"

    def test_user_context_isolated_from_session(self) -> None:
        mgr = DefaultContextManager()
        mgr.update_user_context("u1", theme="dark")
        mgr.update_session_context("s1", mode="voice")

        ctx = mgr.get_context(user_id="u1", session_id="s1")
        assert "theme" in ctx.user.preferences
        assert "theme" not in ctx.session.metadata


class TestBackwardCompatibility:
    def test_nav_context_without_personal(self) -> None:
        """Existing code that creates NavContext without personal_context still works."""
        from core.contracts.context import (
            ConversationContext,
            SessionContext,
            UserContext,
        )

        ctx = NavContext(
            user=UserContext(user_id="u1"),
            session=SessionContext(session_id="s1"),
            conversation=ConversationContext(conversation_id="c1"),
        )
        assert ctx.personal_context is None

    def test_nav_context_with_ambient_data(self) -> None:
        """ambient_data field still works as before."""
        from core.contracts.context import (
            ConversationContext,
            SessionContext,
            UserContext,
        )

        ctx = NavContext(
            user=UserContext(user_id="u1"),
            session=SessionContext(session_id="s1"),
            conversation=ConversationContext(conversation_id="c1"),
            ambient_data={"location": "home"},
        )
        assert ctx.ambient_data["location"] == "home"
        assert ctx.personal_context is None
