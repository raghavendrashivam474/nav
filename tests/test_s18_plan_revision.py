"""S18 Phase 4-5: Plan Revision and Redirection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.work.service import PlanRevisionError, WorkControlError, WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.work import StepStatus, WorkActivityType, WorkPlan, WorkStep
from core.orchestration.orchestrator import Orchestrator


class _EchoCap(Capability):
    def __init__(self, name: str = "research") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "echo"

    def invoke(self, request: Request) -> Response:
        return Response(
            request_id=request.request_id, data={"ok": True}, success=True
        )


@pytest.fixture()
def svc(tmp_path: Path) -> WorkService:
    repo = SQLiteWorkRepository(db_path=tmp_path / "s18_revision.db")
    repo.initialize()
    reg = CapabilityRegistry()
    reg.register(_EchoCap("research"))
    reg.register(_EchoCap("cognition"))
    return WorkService(repository=repo, orchestrator=Orchestrator(reg))


def _plan(n: int = 3) -> WorkPlan:
    return WorkPlan(
        plan_id="p1",
        steps=tuple(
            WorkStep(
                step_id=f"s{i}",
                name=f"S{i}",
                description="d",
                capability="research" if i % 2 == 0 else "cognition",
            )
            for i in range(n)
        ),
    )


class TestPlanRevision:
    def test_revise_pending_steps_safely(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(3))

        snew = WorkStep(
            step_id="s_new",
            name="New step",
            description="new_desc",
            capability="cognition",
        )
        assert w.plan is not None
        new_steps = [w.plan.steps[0], w.plan.steps[1], snew]

        w = svc.revise_plan(w.work_id, new_steps, reason="replace step")
        assert w.plan is not None
        assert w.plan.version == 2
        assert len(w.plan.steps) == 3
        assert w.plan.steps[2].step_id == "s_new"

    def test_completed_steps_are_immutable(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(3))
        w = svc.execute_next_step(w.work_id)

        assert w.plan is not None
        new_steps_removed = [w.plan.steps[1], w.plan.steps[2]]
        with pytest.raises(PlanRevisionError, match="must be immutable step"):
            svc.revise_plan(w.work_id, new_steps_removed, reason="illegal removal")

        mutated_s0 = WorkStep(
            step_id="s0",
            name="Mutated S0",
            description="desc",
            capability="cognition",
            status=StepStatus.COMPLETED,
        )
        new_steps_mutated = [mutated_s0, w.plan.steps[1], w.plan.steps[2]]
        with pytest.raises(PlanRevisionError, match="capability cannot be mutated"):
            svc.revise_plan(w.work_id, new_steps_mutated, reason="illegal mutation")

    def test_plan_history_recorded(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(2))

        snew = WorkStep(
            step_id="s_new",
            name="New",
            description="desc",
            capability="research",
        )
        assert w.plan is not None
        new_steps = [w.plan.steps[0], w.plan.steps[1], snew]

        w = svc.revise_plan(w.work_id, new_steps, reason="added a step")
        assert len(w.metadata["plan_history"]) == 1
        assert w.metadata["plan_history"][0]["version"] == 1
        assert len(w.metadata["plan_history"][0]["steps"]) == 2

    def test_revise_plan_rejects_terminal_work(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(1))
        w = svc.execute_next_step(w.work_id)

        with pytest.raises(WorkControlError, match="terminal"):
            svc.revise_plan(w.work_id, [], reason="too late")


class TestRedirection:
    def test_redirect_changes_objective_only(self, svc: WorkService) -> None:
        w = svc.create_work("PostgreSQL scaling")
        w = svc.set_plan(w.work_id, _plan(2))

        w = svc.redirect_work(
            w.work_id,
            new_objective="Focus on local-first",
            reason="shift topic",
        )
        assert w.objective == "Focus on local-first"
        assert w.plan is not None
        assert w.plan.version == 1

    def test_redirect_changes_objective_and_steps(self, svc: WorkService) -> None:
        w = svc.create_work("Original objective")
        w = svc.set_plan(w.work_id, _plan(2))

        snew = WorkStep(
            step_id="s_new",
            name="New Analysis",
            description="desc",
            capability="cognition",
        )
        assert w.plan is not None
        new_steps = [w.plan.steps[0], snew]

        w = svc.redirect_work(
            w.work_id,
            new_objective="Revised objective",
            new_steps=new_steps,
            reason="full redirection",
        )
        assert w.objective == "Revised objective"
        assert w.plan is not None
        assert w.plan.version == 2
        assert w.plan.steps[1].step_id == "s_new"

    def test_redirection_retains_work_identity(self, svc: WorkService) -> None:
        w = svc.create_work("Original")
        original_id = w.work_id
        w = svc.set_plan(original_id, _plan(2))

        w = svc.redirect_work(original_id, new_objective="Redirected")
        assert w.work_id == original_id

    def test_redirection_emits_activity(self, svc: WorkService) -> None:
        w = svc.create_work("Original")
        w = svc.set_plan(w.work_id, _plan(1))
        w = svc.redirect_work(w.work_id, new_objective="Redirected")

        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.WORK_REDIRECTED in types
