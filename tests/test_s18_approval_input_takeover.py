"""S18 Phase 6-7: Approval, Input, and Takeover tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.work.service import WorkControlError, WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.work import StepStatus, WorkActivityType, WorkPlan, WorkStatus, WorkStep
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
    repo = SQLiteWorkRepository(db_path=tmp_path / "s18_approval.db")
    repo.initialize()
    reg = CapabilityRegistry()
    reg.register(_EchoCap("research"))
    reg.register(_EchoCap("cognition"))
    return WorkService(repository=repo, orchestrator=Orchestrator(reg))


def _approval_plan() -> WorkPlan:
    s0 = WorkStep(
        step_id="s0",
        name="Step 0",
        description="d0",
        capability="research",
    )
    s1 = WorkStep(
        step_id="s1",
        name="Step 1 Sensitive",
        description="d1",
        capability="cognition",
        metadata={"requires_approval": True},
        dependencies=("s0",),
    )
    return WorkPlan(plan_id="p_appr", steps=(s0, s1))


class TestApproval:
    def test_approval_gate_intercepts_execution(self, svc: WorkService) -> None:
        w = svc.create_work("Approval test")
        w = svc.set_plan(w.work_id, _approval_plan())

        # Step 0 completes normally
        w = svc.execute_next_step(w.work_id)
        assert w.plan is not None
        assert w.plan.steps[0].status == StepStatus.COMPLETED

        # Step 1 requires approval -> should enter WAITING_FOR_APPROVAL
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.WAITING_FOR_APPROVAL
        assert w.plan is not None
        assert w.plan.steps[1].status == StepStatus.WAITING_FOR_APPROVAL

        # Trying to advance while waiting for approval raises WorkControlError
        with pytest.raises(WorkControlError, match="waiting"):
            svc.execute_next_step(w.work_id)

    def test_approve_step_resumes_and_executes(self, svc: WorkService) -> None:
        w = svc.create_work("Approve test")
        w = svc.set_plan(w.work_id, _approval_plan())
        w = svc.execute_next_step(w.work_id)
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.WAITING_FOR_APPROVAL

        # Human approves
        w = svc.approve_step(w.work_id, "s1")
        assert w.status == WorkStatus.RUNNING
        assert w.plan is not None
        assert w.plan.steps[1].status == StepStatus.READY

        # Next execution succeeds
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.COMPLETED
        assert w.plan is not None
        assert w.plan.steps[1].status == StepStatus.COMPLETED

    def test_approve_with_modified_payload(self, svc: WorkService) -> None:
        w = svc.create_work("Modify test")
        w = svc.set_plan(w.work_id, _approval_plan())
        w = svc.execute_next_step(w.work_id)
        w = svc.execute_next_step(w.work_id)

        # Human approves with modified parameters
        w = svc.approve_step(w.work_id, "s1", modified_payload={"custom": "param"})
        assert w.plan is not None
        assert w.plan.steps[1].input_payload == {"custom": "param"}

        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.PLAN_REVISED in types
        assert WorkActivityType.APPROVAL_GRANTED in types

    def test_reject_step_pauses_work(self, svc: WorkService) -> None:
        w = svc.create_work("Reject test")
        w = svc.set_plan(w.work_id, _approval_plan())
        w = svc.execute_next_step(w.work_id)
        w = svc.execute_next_step(w.work_id)

        # Human rejects action
        w = svc.reject_step(w.work_id, "s1", reason="Unsafe operation")
        assert w.status == WorkStatus.PAUSED
        assert w.plan is not None
        assert w.plan.steps[1].status == StepStatus.FAILED
        assert "Rejected by human: Unsafe operation" in str(w.plan.steps[1].error)

        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.APPROVAL_REJECTED in types


class TestInput:
    def test_request_and_provide_input(self, svc: WorkService) -> None:
        w = svc.create_work("Input test")
        plan = WorkPlan(
            plan_id="p_in",
            steps=(
                WorkStep(
                    step_id="s0",
                    name="Step 0",
                    description="d0",
                    capability="cognition",
                ),
            ),
        )
        w = svc.set_plan(w.work_id, plan)
        w = svc.request_input(w.work_id, step_id="s0", prompt="What database?")
        assert w.status == WorkStatus.WAITING_FOR_INPUT
        assert w.plan is not None
        assert w.plan.steps[0].status == StepStatus.WAITING_FOR_INPUT

        # Provide input
        w = svc.provide_input(w.work_id, {"db": "postgres"}, step_id="s0")
        assert w.status == WorkStatus.RUNNING
        assert w.plan is not None
        assert w.plan.steps[0].status == StepStatus.READY
        assert w.plan.steps[0].input_payload.get("db") == "postgres"


class TestTakeover:
    def test_takeover_and_return_control(self, svc: WorkService) -> None:
        w = svc.create_work("Takeover test")
        plan = WorkPlan(
            plan_id="p_to",
            steps=(
                WorkStep(
                    step_id="s0",
                    name="Step 0",
                    description="d0",
                    capability="research",
                ),
            ),
        )
        w = svc.set_plan(w.work_id, plan)

        # Human takes over
        w = svc.take_over(w.work_id, reason="Manual intervention")
        assert w.status == WorkStatus.PAUSED
        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.HUMAN_TAKEOVER in types

        # Return control
        w = svc.return_control(w.work_id, reason="Done editing")
        assert w.status in (WorkStatus.READY, WorkStatus.RUNNING)
        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.CONTROL_RETURNED in types
