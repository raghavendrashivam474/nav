"""Tests for S12 personal context dataclasses."""

from core.contracts.context import (
    Commitment,
    CurrentFocus,
    Goal,
    PersonalContext,
    Project,
)


class TestProject:
    def test_create_minimal(self) -> None:
        p = Project(project_id="p1", name="NAV")
        assert p.project_id == "p1"
        assert p.name == "NAV"
        assert p.status == "active"
        assert p.priority == 0

    def test_create_full(self) -> None:
        p = Project(
            project_id="p1",
            name="NAV",
            status="active",
            description="AI assistant",
            priority=1,
            current_focus="S12",
        )
        assert p.current_focus == "S12"

    def test_frozen(self) -> None:
        p = Project(project_id="p1", name="NAV")
        try:
            p.name = "changed"  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass


class TestGoal:
    def test_create(self) -> None:
        g = Goal(goal_id="g1", description="Build NAV v1")
        assert g.status == "active"
        assert g.project_id is None

    def test_with_project(self) -> None:
        g = Goal(goal_id="g1", description="Build NAV v1", project_id="p1")
        assert g.project_id == "p1"


class TestCommitment:
    def test_create(self) -> None:
        c = Commitment(commitment_id="c1", description="Finish S12")
        assert c.status == "active"


class TestCurrentFocus:
    def test_empty(self) -> None:
        f = CurrentFocus()
        assert f.project_id is None
        assert f.activity == ""

    def test_with_values(self) -> None:
        f = CurrentFocus(project_id="p1", activity="coding", topic="context")
        assert f.topic == "context"


class TestPersonalContext:
    def test_empty(self) -> None:
        pc = PersonalContext()
        assert pc.projects == ()
        assert pc.goals == ()
        assert pc.commitments == ()
        assert pc.current_focus is None

    def test_with_data(self) -> None:
        pc = PersonalContext(
            projects=(Project(project_id="p1", name="NAV"),),
            goals=(Goal(goal_id="g1", description="v1"),),
            commitments=(Commitment(commitment_id="c1", description="ship"),),
            current_focus=CurrentFocus(project_id="p1"),
        )
        assert len(pc.projects) == 1
        assert pc.current_focus is not None
        assert pc.current_focus.project_id == "p1"
