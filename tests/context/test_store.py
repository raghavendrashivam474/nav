"""Tests for S12 ContextStore."""

from core.context.store import ContextStore
from core.contracts.context import (
    Commitment,
    CurrentFocus,
    Goal,
    Project,
)


class TestUserStore:
    def test_get_creates_default(self) -> None:
        store = ContextStore()
        user = store.get_user("u1")
        assert user.user_id == "u1"
        assert user.preferences == {}

    def test_update_merges_preferences(self) -> None:
        store = ContextStore()
        store.update_user("u1", theme="dark")
        store.update_user("u1", language="en")
        user = store.get_user("u1")
        assert user.preferences == {"theme": "dark", "language": "en"}

    def test_update_overwrites_key(self) -> None:
        store = ContextStore()
        store.update_user("u1", theme="dark")
        store.update_user("u1", theme="light")
        assert store.get_user("u1").preferences["theme"] == "light"


class TestSessionStore:
    def test_get_creates_default(self) -> None:
        store = ContextStore()
        s = store.get_session("s1")
        assert s.session_id == "s1"

    def test_update_merges_metadata(self) -> None:
        store = ContextStore()
        store.update_session("s1", mode="voice")
        store.update_session("s1", channel="mobile")
        s = store.get_session("s1")
        assert s.metadata == {"mode": "voice", "channel": "mobile"}


class TestConversationStore:
    def test_get_creates_default(self) -> None:
        store = ContextStore()
        c = store.get_conversation("c1")
        assert c.turns_count == 0

    def test_turns_increment(self) -> None:
        store = ContextStore()
        store.update_conversation("c1", turns_increment=3)
        store.update_conversation("c1", turns_increment=2)
        assert store.get_conversation("c1").turns_count == 5

    def test_history_summary_preserved(self) -> None:
        store = ContextStore()
        store.update_conversation("c1", history_summary="discussed NAV")
        store.update_conversation("c1", turns_increment=1)
        assert store.get_conversation("c1").history_summary == "discussed NAV"

    def test_history_summary_replaced(self) -> None:
        store = ContextStore()
        store.update_conversation("c1", history_summary="old")
        store.update_conversation("c1", history_summary="new")
        assert store.get_conversation("c1").history_summary == "new"


class TestPersonalContextStore:
    def test_get_creates_empty(self) -> None:
        store = ContextStore()
        pc = store.get_personal("u1")
        assert pc.projects == ()

    def test_add_project(self) -> None:
        store = ContextStore()
        store.add_project("u1", Project(project_id="p1", name="NAV"))
        pc = store.get_personal("u1")
        assert len(pc.projects) == 1
        assert pc.projects[0].name == "NAV"

    def test_add_project_replaces_same_id(self) -> None:
        store = ContextStore()
        store.add_project("u1", Project(project_id="p1", name="NAV"))
        store.add_project("u1", Project(project_id="p1", name="NAV v2"))
        pc = store.get_personal("u1")
        assert len(pc.projects) == 1
        assert pc.projects[0].name == "NAV v2"

    def test_remove_project(self) -> None:
        store = ContextStore()
        store.add_project("u1", Project(project_id="p1", name="NAV"))
        store.add_project("u1", Project(project_id="p2", name="Other"))
        store.remove_project("u1", "p1")
        pc = store.get_personal("u1")
        assert len(pc.projects) == 1
        assert pc.projects[0].project_id == "p2"

    def test_multiple_projects_isolated(self) -> None:
        store = ContextStore()
        store.add_project("u1", Project(project_id="p1", name="A"))
        store.add_project("u1", Project(project_id="p2", name="B"))
        pc = store.get_personal("u1")
        assert len(pc.projects) == 2
        ids = {p.project_id for p in pc.projects}
        assert ids == {"p1", "p2"}

    def test_add_goal(self) -> None:
        store = ContextStore()
        store.add_goal("u1", Goal(goal_id="g1", description="Build v1"))
        pc = store.get_personal("u1")
        assert len(pc.goals) == 1

    def test_remove_goal(self) -> None:
        store = ContextStore()
        store.add_goal("u1", Goal(goal_id="g1", description="Build v1"))
        store.remove_goal("u1", "g1")
        assert store.get_personal("u1").goals == ()

    def test_goal_status_update_via_replace(self) -> None:
        store = ContextStore()
        store.add_goal("u1", Goal(goal_id="g1", description="Build v1"))
        store.add_goal("u1", Goal(goal_id="g1", description="Build v1", status="done"))
        pc = store.get_personal("u1")
        assert len(pc.goals) == 1
        assert pc.goals[0].status == "done"

    def test_add_commitment(self) -> None:
        store = ContextStore()
        store.add_commitment("u1", Commitment(commitment_id="c1", description="Ship S12"))
        assert len(store.get_personal("u1").commitments) == 1

    def test_remove_commitment(self) -> None:
        store = ContextStore()
        store.add_commitment("u1", Commitment(commitment_id="c1", description="Ship S12"))
        store.remove_commitment("u1", "c1")
        assert store.get_personal("u1").commitments == ()

    def test_set_focus(self) -> None:
        store = ContextStore()
        focus = CurrentFocus(project_id="p1", activity="coding")
        store.set_focus("u1", focus)
        pc = store.get_personal("u1")
        assert pc.current_focus is not None
        assert pc.current_focus.activity == "coding"

    def test_replace_focus(self) -> None:
        store = ContextStore()
        store.set_focus("u1", CurrentFocus(project_id="p1"))
        store.set_focus("u1", CurrentFocus(project_id="p2"))
        focus = store.get_personal("u1").current_focus
        assert focus is not None
        assert focus.project_id == "p2"

    def test_clear_focus(self) -> None:
        store = ContextStore()
        store.set_focus("u1", CurrentFocus(project_id="p1"))
        store.set_focus("u1", None)
        assert store.get_personal("u1").current_focus is None

    def test_user_isolation(self) -> None:
        store = ContextStore()
        store.add_project("u1", Project(project_id="p1", name="A"))
        store.add_project("u2", Project(project_id="p2", name="B"))
        assert len(store.get_personal("u1").projects) == 1
        assert len(store.get_personal("u2").projects) == 1
        assert store.get_personal("u1").projects[0].project_id == "p1"
        assert store.get_personal("u2").projects[0].project_id == "p2"
