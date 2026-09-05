"""S18 Phase 2-3: Pause enforcement, resume, cancel, intervention."""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.work.service import WorkControlError, WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.work import WorkActivityType, WorkPlan, WorkStatus, WorkStep
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
    repo = SQLiteWorkRepository(db_path=tmp_path / "s18.db")
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


# =================================================================
# Pause enforcement
# =================================================================


class TestPauseEnforcement:
    def test_pause_ready_work(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.pause_work(w.work_id)
        assert w.status == WorkStatus.PAUSED

    def test_pause_running_work(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.execute_next_step(w.work_id)
        w = svc.pause_work(w.work_id)
        assert w.status == WorkStatus.PAUSED

    def test_paused_cannot_execute(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.pause_work(w.work_id)
        with pytest.raises(WorkControlError, match="paused"):
            svc.execute_next_step(w.work_id)

    def test_paused_cannot_run_bounded(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.pause_work(w.work_id)
        w = svc.run_bounded(w.work_id, max_steps=5)
        assert w.status == WorkStatus.PAUSED
        assert len(w.completed_steps()) == 0

    def test_pause_idempotent(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.pause_work(w.work_id)
        w2 = svc.pause_work(w.work_id)
        assert w2.status == WorkStatus.PAUSED

    def test_pause_rejects_completed(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(1))
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.COMPLETED
        with pytest.raises(WorkControlError, match="terminal"):
            svc.pause_work(w.work_id)

    def test_pause_rejects_cancelled(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.cancel_work(w.work_id)
        with pytest.raises(WorkControlError, match="terminal"):
            svc.pause_work(w.work_id)

    def test_pause_emits_activity(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.pause_work(w.work_id)
        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.WORK_PAUSED in types


# =================================================================
# Resume
# =================================================================


class TestResume:
    def test_resume_paused(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.pause_work(w.work_id)
        w = svc.resume_work(w.work_id)
        assert w.status in (WorkStatus.READY, WorkStatus.RUNNING)

    def test_resume_rejects_running(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.execute_next_step(w.work_id)
        with pytest.raises(WorkControlError, match="Cannot resume"):
            svc.resume_work(w.work_id)

    def test_resume_preserves_completed(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(3))
        w = svc.execute_next_step(w.work_id)
        w = svc.pause_work(w.work_id)
        w = svc.resume_work(w.work_id)
        assert len(w.completed_steps()) == 1

    def test_resume_then_continue(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(2))
        w = svc.execute_next_step(w.work_id)
        w = svc.pause_work(w.work_id)
        w = svc.resume_work(w.work_id)
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.COMPLETED

    def test_resume_emits_activity(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.pause_work(w.work_id)
        w = svc.resume_work(w.work_id)
        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.WORK_RESUMED in types


# =================================================================
# Cancel
# =================================================================


class TestCancel:
    def test_cancel_running(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.execute_next_step(w.work_id)
        w = svc.cancel_work(w.work_id)
        assert w.status == WorkStatus.CANCELLED

    def test_cancel_paused(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.pause_work(w.work_id)
        w = svc.cancel_work(w.work_id)
        assert w.status == WorkStatus.CANCELLED

    def test_cancel_idempotent(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.cancel_work(w.work_id)
        w2 = svc.cancel_work(w.work_id)
        assert w2.status == WorkStatus.CANCELLED

    def test_cancel_rejects_completed(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(1))
        w = svc.execute_next_step(w.work_id)
        with pytest.raises(WorkControlError, match="Cannot cancel"):
            svc.cancel_work(w.work_id)

    def test_cancelled_cannot_execute(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan())
        w = svc.cancel_work(w.work_id)
        with pytest.raises(WorkControlError, match="terminal"):
            svc.execute_next_step(w.work_id)

    def test_cancelled_cannot_resume(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.cancel_work(w.work_id)
        with pytest.raises(WorkControlError, match="Cannot resume"):
            svc.resume_work(w.work_id)

    def test_cancel_emits_activity(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.cancel_work(w.work_id)
        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.WORK_CANCELLED in types

    def test_cancelled_run_bounded_noop(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(3))
        w = svc.cancel_work(w.work_id)
        w = svc.run_bounded(w.work_id, max_steps=5)
        assert w.status == WorkStatus.CANCELLED
        assert len(w.completed_steps()) == 0


# =================================================================
# Intervention
# =================================================================


class TestIntervention:
    def test_intervention_blocks_next_step(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(3))
        w = svc.execute_next_step(w.work_id)
        w = svc.request_intervention(w.work_id, reason="hold")
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.PAUSED

    def test_intervention_rejects_terminal(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(1))
        w = svc.execute_next_step(w.work_id)
        with pytest.raises(WorkControlError, match="terminal"):
            svc.request_intervention(w.work_id)

    def test_intervention_emits_activity(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.request_intervention(w.work_id, reason="test")
        types = [a.activity_type for a in w.activity_log]
        assert WorkActivityType.INTERVENTION_REQUESTED in types

    def test_resume_clears_intervention(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.set_plan(w.work_id, _plan(2))
        w = svc.request_intervention(w.work_id, reason="hold")
        w = svc.execute_next_step(w.work_id)
        assert w.status == WorkStatus.PAUSED
        w = svc.resume_work(w.work_id)
        assert w.status in (WorkStatus.READY, WorkStatus.RUNNING)
        assert w.metadata.get("control", {}).get("pending") is False

    def test_intervention_persists(self, svc: WorkService) -> None:
        w = svc.create_work("t")
        w = svc.request_intervention(w.work_id, reason="check this")
        fetched = svc.get_work(w.work_id)
        assert fetched is not None
        assert fetched.metadata["control"]["pending"] is True
        assert fetched.metadata["control"]["reason"] == "check this"
