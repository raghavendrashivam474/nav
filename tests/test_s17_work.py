"""Comprehensive test suite for S17: Technical Intelligence & Agentic Workflows.

Covers:
- Model immutability and helpers
- SQLite repository CRUD, search, and activity persistence
- Deterministic and AI-assisted planning
- Step evaluation
- Step-by-step and bounded execution
- Dependency resolution
- Failure recording and retry
- Context integration
- Recovery across repository instances
- Capability boundary (Orchestrator integration)
- Activity logging
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from capabilities.work.capability import WorkCapability
from capabilities.work.evaluator import DeterministicEvaluator
from capabilities.work.planner import AIPlanner, DeterministicPlanner
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.capability import Capability, Request, Response
from core.contracts.context import (
    ConversationContext,
    CurrentFocus,
    NavContext,
    PersonalContext,
    SessionContext,
    UserContext,
)
from core.contracts.work import (
    StepStatus,
    Work,
    WorkActivity,
    WorkActivityType,
    WorkPlan,
    WorkQuery,
    WorkStatus,
    WorkStep,
)
from core.orchestration.orchestrator import Orchestrator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def work_repo(tmp_path: Path) -> SQLiteWorkRepository:
    repo = SQLiteWorkRepository(db_path=tmp_path / "test_work.db")
    repo.initialize()
    return repo


@pytest.fixture()
def planner() -> DeterministicPlanner:
    return DeterministicPlanner()


@pytest.fixture()
def evaluator() -> DeterministicEvaluator:
    return DeterministicEvaluator()


class _EchoCapability(Capability):
    """Test capability that echoes its input as output."""

    def __init__(self, cap_name: str = "research", fail: bool = False) -> None:
        self._name = cap_name
        self._fail = fail

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "0.1.0"

    @property
    def description(self) -> str:
        return "Echo test capability"

    def invoke(self, request: Request) -> Response:
        if self._fail:
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error="Simulated failure",
            )
        return Response(
            request_id=request.request_id,
            data={"echo": request.payload, "result": "ok"},
            success=True,
        )


@pytest.fixture()
def orchestrator() -> Orchestrator:
    registry = CapabilityRegistry()
    registry.register(_EchoCapability("research"))
    registry.register(_EchoCapability("cognition"))
    registry.register(_EchoCapability("memory"))
    return Orchestrator(registry)


@pytest.fixture()
def failing_orchestrator() -> Orchestrator:
    registry = CapabilityRegistry()
    registry.register(_EchoCapability("research", fail=True))
    registry.register(_EchoCapability("cognition", fail=True))
    return Orchestrator(registry)


@pytest.fixture()
def work_service(
    work_repo: SQLiteWorkRepository, orchestrator: Orchestrator
) -> WorkService:
    return WorkService(
        repository=work_repo,
        orchestrator=orchestrator,
    )


def _make_plan(n_steps: int = 2, with_deps: bool = False) -> WorkPlan:
    steps: list[WorkStep] = []
    for i in range(n_steps):
        deps = (steps[i - 1].step_id,) if with_deps and i > 0 else ()
        steps.append(
            WorkStep(
                step_id=f"s{i}",
                name=f"Step {i}",
                description=f"Test step {i}",
                capability="research" if i % 2 == 0 else "cognition",
                input_payload={"q": f"query_{i}"},
                dependencies=deps,
            )
        )
    return WorkPlan(plan_id="plan_test", steps=tuple(steps))


# ===========================================================================
# 1. Model Tests
# ===========================================================================


class TestWorkModels:
    def test_work_step_frozen(self) -> None:
        step = WorkStep(step_id="s1", name="T", description="D", capability="research")
        with pytest.raises(AttributeError):
            step.status = StepStatus.RUNNING  # type: ignore[misc]

    def test_work_frozen(self) -> None:
        w = Work(work_id="w1", objective="Test")
        with pytest.raises(AttributeError):
            w.status = WorkStatus.RUNNING  # type: ignore[misc]

    def test_plan_ready_steps_no_deps(self) -> None:
        plan = _make_plan(3)
        ready = plan.ready_steps()
        assert len(ready) == 3

    def test_plan_ready_steps_with_deps(self) -> None:
        plan = _make_plan(3, with_deps=True)
        ready = plan.ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s0"

    def test_plan_ready_steps_after_completion(self) -> None:
        plan = _make_plan(3, with_deps=True)
        s0_done = replace(plan.steps[0], status=StepStatus.COMPLETED)
        plan = replace(plan, steps=(s0_done, plan.steps[1], plan.steps[2]))
        ready = plan.ready_steps()
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

    def test_plan_is_all_completed(self) -> None:
        plan = _make_plan(2)
        assert not plan.is_all_completed()
        done = tuple(replace(s, status=StepStatus.COMPLETED) for s in plan.steps)
        plan = replace(plan, steps=done)
        assert plan.is_all_completed()

    def test_plan_has_failed_step(self) -> None:
        plan = _make_plan(2)
        assert not plan.has_failed_step()
        failed = replace(plan.steps[0], status=StepStatus.FAILED)
        plan = replace(plan, steps=(failed, plan.steps[1]))
        assert plan.has_failed_step()

    def test_work_helpers(self) -> None:
        plan = _make_plan(3)
        w = Work(work_id="w1", objective="Test", plan=plan, current_step_id="s1")
        assert w.get_current_step() is not None
        assert w.get_current_step().step_id == "s1"
        assert len(w.completed_steps()) == 0
        assert len(w.pending_steps()) == 3


# ===========================================================================
# 2. Repository Tests
# ===========================================================================


class TestWorkRepository:
    def test_save_and_get(self, work_repo: SQLiteWorkRepository) -> None:
        w = Work(
            work_id="w1",
            objective="Test objective",
            created_at="t",
            updated_at="t",
        )
        assert work_repo.save(w) is True
        fetched = work_repo.get("w1")
        assert fetched is not None
        assert fetched.objective == "Test objective"

    def test_duplicate_save(self, work_repo: SQLiteWorkRepository) -> None:
        w = Work(work_id="w1", objective="T", created_at="t", updated_at="t")
        assert work_repo.save(w) is True
        assert work_repo.save(w) is False

    def test_get_missing(self, work_repo: SQLiteWorkRepository) -> None:
        assert work_repo.get("nonexistent") is None

    def test_update(self, work_repo: SQLiteWorkRepository) -> None:
        w = Work(work_id="w1", objective="Original", created_at="t", updated_at="t")
        work_repo.save(w)
        updated = replace(w, objective="Modified")
        assert work_repo.update(updated) is True
        fetched = work_repo.get("w1")
        assert fetched is not None
        assert fetched.objective == "Modified"

    def test_update_missing(self, work_repo: SQLiteWorkRepository) -> None:
        w = Work(work_id="w1", objective="T", created_at="t", updated_at="t")
        assert work_repo.update(w) is False

    def test_delete(self, work_repo: SQLiteWorkRepository) -> None:
        w = Work(work_id="w1", objective="T", created_at="t", updated_at="t")
        work_repo.save(w)
        assert work_repo.delete("w1") is True
        assert work_repo.get("w1") is None

    def test_delete_missing(self, work_repo: SQLiteWorkRepository) -> None:
        assert work_repo.delete("nope") is False

    def test_find_by_status(self, work_repo: SQLiteWorkRepository) -> None:
        w1 = Work(
            work_id="w1",
            objective="A",
            status=WorkStatus.RUNNING,
            created_at="t",
            updated_at="t",
        )
        w2 = Work(
            work_id="w2",
            objective="B",
            status=WorkStatus.COMPLETED,
            created_at="t",
            updated_at="t",
        )
        work_repo.save(w1)
        work_repo.save(w2)
        results = work_repo.find(WorkQuery(status="running"))
        assert len(results) == 1
        assert results[0].work_id == "w1"

    def test_find_by_text(self, work_repo: SQLiteWorkRepository) -> None:
        w = Work(
            work_id="w1",
            objective="PostgreSQL scalability",
            created_at="t",
            updated_at="t",
        )
        work_repo.save(w)
        results = work_repo.find(WorkQuery(query_text="PostgreSQL"))
        assert len(results) == 1

    def test_persist_plan_and_activity(self, work_repo: SQLiteWorkRepository) -> None:
        plan = _make_plan(2)
        activity = WorkActivity(
            timestamp="t",
            activity_type=WorkActivityType.WORK_CREATED,
            description="test",
        )
        w = Work(
            work_id="w1",
            objective="T",
            plan=plan,
            activity_log=(activity,),
            created_at="t",
            updated_at="t",
        )
        work_repo.save(w)
        fetched = work_repo.get("w1")
        assert fetched is not None
        assert fetched.plan is not None
        assert len(fetched.plan.steps) == 2
        assert len(fetched.activity_log) == 1

    def test_recovery_across_instances(self, tmp_path: Path) -> None:
        db = tmp_path / "recovery.db"
        repo1 = SQLiteWorkRepository(db_path=db)
        repo1.initialize()
        plan = _make_plan(2)
        w = Work(
            work_id="w1",
            objective="Recover me",
            plan=plan,
            status=WorkStatus.RUNNING,
            current_step_id="s0",
            created_at="t",
            updated_at="t",
        )
        repo1.save(w)

        repo2 = SQLiteWorkRepository(db_path=db)
        repo2.initialize()
        fetched = repo2.get("w1")
        assert fetched is not None
        assert fetched.status == WorkStatus.RUNNING
        assert fetched.current_step_id == "s0"
        assert fetched.plan is not None
        assert len(fetched.plan.steps) == 2


# ===========================================================================
# 3. Planner Tests
# ===========================================================================


class TestPlanner:
    def test_deterministic_research(self, planner: DeterministicPlanner) -> None:
        plan = planner.create_plan("Research quantum computing trends")
        assert len(plan.steps) >= 2
        assert plan.steps[0].capability == "research"

    def test_deterministic_comparison(self, planner: DeterministicPlanner) -> None:
        plan = planner.create_plan("Compare PostgreSQL vs MySQL")
        assert len(plan.steps) >= 2
        last = plan.steps[-1]
        assert len(last.dependencies) > 0

    def test_deterministic_analysis(self, planner: DeterministicPlanner) -> None:
        plan = planner.create_plan("Analyse the performance bottleneck")
        assert len(plan.steps) >= 2

    def test_deterministic_generic(self, planner: DeterministicPlanner) -> None:
        plan = planner.create_plan("Do something unspecified")
        assert len(plan.steps) >= 1

    def test_ai_planner_valid_json(self) -> None:
        class _MockGateway(AIGateway):
            def generate(self, request: AIRequest) -> AIResponse:
                return AIResponse(
                    content=json.dumps({
                        "steps": [
                            {
                                "name": "S1",
                                "description": "D1",
                                "capability": "research",
                                "input_payload": {},
                                "dependencies": [],
                            },
                            {
                                "name": "S2",
                                "description": "D2",
                                "capability": "cognition",
                                "input_payload": {},
                                "dependencies": [0],
                            },
                        ]
                    }),
                    model_used="mock",
                )

        ai_planner = AIPlanner(gateway=_MockGateway())
        plan = ai_planner.create_plan("Test objective")
        assert len(plan.steps) == 2
        assert len(plan.steps[1].dependencies) == 1

    def test_ai_planner_malformed_fallback(self) -> None:
        class _BadGateway(AIGateway):
            def generate(self, request: AIRequest) -> AIResponse:
                return AIResponse(content="this is not json", model_used="mock")

        ai_planner = AIPlanner(gateway=_BadGateway())
        plan = ai_planner.create_plan("Test objective")
        assert len(plan.steps) >= 1

    def test_ai_planner_invalid_capability_sanitized(self) -> None:
        class _MockGateway(AIGateway):
            def generate(self, request: AIRequest) -> AIResponse:
                return AIResponse(
                    content=json.dumps({
                        "steps": [
                            {
                                "name": "S1",
                                "description": "D1",
                                "capability": "hacking",
                                "input_payload": {},
                                "dependencies": [],
                            },
                        ]
                    }),
                    model_used="mock",
                )

        ai_planner = AIPlanner(gateway=_MockGateway())
        plan = ai_planner.create_plan("Test")
        assert plan.steps[0].capability == "cognition"


# ===========================================================================
# 4. Evaluator Tests
# ===========================================================================


class TestEvaluator:
    def test_success(self, evaluator: DeterministicEvaluator) -> None:
        step = WorkStep(step_id="s1", name="T", description="D", capability="research")
        status, err = evaluator.evaluate_step(step, {"data": "ok"}, True)
        assert status == StepStatus.COMPLETED
        assert err is None

    def test_failure_with_retries(self, evaluator: DeterministicEvaluator) -> None:
        step = WorkStep(
            step_id="s1",
            name="T",
            description="D",
            capability="research",
            retry_count=0,
            max_retries=2,
        )
        status, err = evaluator.evaluate_step(step, {"error": "timeout"}, False)
        assert status == StepStatus.FAILED
        assert err is not None

    def test_failure_no_retries(self, evaluator: DeterministicEvaluator) -> None:
        step = WorkStep(
            step_id="s1",
            name="T",
            description="D",
            capability="research",
            retry_count=2,
            max_retries=2,
        )
        status, err = evaluator.evaluate_step(step, {}, False)
        assert status == StepStatus.FAILED


# ===========================================================================
# 5. Execution Tests
# ===========================================================================


class TestExecution:
    def test_create_and_plan(self, work_service: WorkService) -> None:
        work = work_service.create_work("Test objective")
        assert work.status == WorkStatus.PENDING
        work = work_service.auto_plan(work.work_id)
        assert work.status == WorkStatus.READY
        assert work.plan is not None
        assert len(work.plan.steps) >= 1

    def test_execute_single_step(self, work_service: WorkService) -> None:
        work = work_service.create_work("Test")
        plan = _make_plan(1)
        work = work_service.set_plan(work.work_id, plan)
        work = work_service.execute_next_step(work.work_id)
        assert work.plan is not None
        assert work.plan.steps[0].status == StepStatus.COMPLETED
        assert work.status == WorkStatus.COMPLETED

    def test_execute_multiple_steps(self, work_service: WorkService) -> None:
        work = work_service.create_work("Multi-step")
        plan = _make_plan(3)
        work = work_service.set_plan(work.work_id, plan)
        for _ in range(3):
            work = work_service.execute_next_step(work.work_id)
        assert work.status == WorkStatus.COMPLETED
        assert len(work.completed_steps()) == 3

    def test_execute_with_dependencies(self, work_service: WorkService) -> None:
        work = work_service.create_work("Deps")
        plan = _make_plan(3, with_deps=True)
        work = work_service.set_plan(work.work_id, plan)
        work = work_service.execute_next_step(work.work_id)
        assert work.plan is not None
        assert work.plan.steps[0].status == StepStatus.COMPLETED
        assert work.plan.steps[1].status == StepStatus.PENDING
        work = work_service.execute_next_step(work.work_id)
        assert work.plan.steps[1].status == StepStatus.COMPLETED

    def test_run_bounded(self, work_service: WorkService) -> None:
        work = work_service.create_work("Bounded")
        plan = _make_plan(5)
        work = work_service.set_plan(work.work_id, plan)
        work = work_service.run_bounded(work.work_id, max_steps=3)
        assert len(work.completed_steps()) == 3
        assert work.status == WorkStatus.RUNNING

    def test_run_bounded_completes(self, work_service: WorkService) -> None:
        work = work_service.create_work("Bounded complete")
        plan = _make_plan(2)
        work = work_service.set_plan(work.work_id, plan)
        work = work_service.run_bounded(work.work_id, max_steps=5)
        assert work.status == WorkStatus.COMPLETED

    def test_run_bounded_auto_plans(self, work_service: WorkService) -> None:
        work = work_service.create_work("Auto plan")
        work = work_service.run_bounded(work.work_id, max_steps=5)
        assert work.plan is not None
        assert work.status in (WorkStatus.COMPLETED, WorkStatus.RUNNING)


# ===========================================================================
# 6. Failure & Retry Tests
# ===========================================================================


class TestFailure:
    def test_failed_step_recorded(
        self, work_repo: SQLiteWorkRepository, failing_orchestrator: Orchestrator
    ) -> None:
        svc = WorkService(repository=work_repo, orchestrator=failing_orchestrator)
        work = svc.create_work("Will fail")
        plan = _make_plan(1)
        work = svc.set_plan(work.work_id, plan)
        work = svc.execute_next_step(work.work_id)
        assert work.plan is not None
        assert work.plan.steps[0].status == StepStatus.FAILED
        assert work.plan.steps[0].error is not None

    def test_no_silent_infinite_retry(
        self, work_repo: SQLiteWorkRepository, failing_orchestrator: Orchestrator
    ) -> None:
        svc = WorkService(repository=work_repo, orchestrator=failing_orchestrator)
        work = svc.create_work("No infinite retry")
        plan = _make_plan(1)
        work = svc.set_plan(work.work_id, plan)
        work = svc.run_bounded(work.work_id, max_steps=10)
        assert work.status in (WorkStatus.FAILED, WorkStatus.BLOCKED)

    def test_work_inspectable_after_failure(
        self, work_repo: SQLiteWorkRepository, failing_orchestrator: Orchestrator
    ) -> None:
        svc = WorkService(repository=work_repo, orchestrator=failing_orchestrator)
        work = svc.create_work("Inspect me")
        plan = _make_plan(2)
        work = svc.set_plan(work.work_id, plan)
        work = svc.execute_next_step(work.work_id)
        fetched = svc.get_work(work.work_id)
        assert fetched is not None
        assert fetched.plan is not None
        assert fetched.plan.steps[0].error is not None

    def test_retry_step(
        self, work_repo: SQLiteWorkRepository, failing_orchestrator: Orchestrator
    ) -> None:
        svc = WorkService(repository=work_repo, orchestrator=failing_orchestrator)
        work = svc.create_work("Retry test")
        step = WorkStep(
            step_id="s0",
            name="S",
            description="D",
            capability="research",
            max_retries=2,
        )
        plan = WorkPlan(plan_id="p1", steps=(step,))
        work = svc.set_plan(work.work_id, plan)
        work = svc.execute_next_step(work.work_id)
        assert work.plan is not None
        assert work.plan.steps[0].status == StepStatus.FAILED
        work = svc.retry_step(work.work_id, "s0")
        assert work.plan is not None
        assert work.plan.steps[0].status == StepStatus.READY
        assert work.plan.steps[0].retry_count == 1


# ===========================================================================
# 7. Context Integration Tests
# ===========================================================================


class TestContextIntegration:
    def test_create_from_context(self, work_service: WorkService) -> None:
        ctx = NavContext(
            user=UserContext(user_id="u1"),
            session=SessionContext(session_id="s1"),
            conversation=ConversationContext(conversation_id="c1"),
            personal_context=PersonalContext(
                current_focus=CurrentFocus(
                    project_id="p1", goal_id="g1", topic="databases"
                ),
            ),
        )
        work = work_service.create_from_context(ctx, "Evaluate DB options")
        assert work.project_id == "p1"
        assert work.goal_id == "g1"
        assert "databases" in work.tags


# ===========================================================================
# 8. Activity Logging Tests
# ===========================================================================


class TestActivity:
    def test_activity_on_create(self, work_service: WorkService) -> None:
        work = work_service.create_work("Activity test")
        assert len(work.activity_log) >= 1
        assert work.activity_log[0].activity_type == WorkActivityType.WORK_CREATED

    def test_activity_on_plan(self, work_service: WorkService) -> None:
        work = work_service.create_work("Plan activity")
        work = work_service.auto_plan(work.work_id)
        types = [a.activity_type for a in work.activity_log]
        assert WorkActivityType.PLAN_ESTABLISHED in types

    def test_activity_on_execution(self, work_service: WorkService) -> None:
        work = work_service.create_work("Exec activity")
        plan = _make_plan(1)
        work = work_service.set_plan(work.work_id, plan)
        work = work_service.execute_next_step(work.work_id)
        types = [a.activity_type for a in work.activity_log]
        assert WorkActivityType.STEP_STARTED in types
        assert WorkActivityType.STEP_COMPLETED in types


# ===========================================================================
# 9. Capability Boundary Tests
# ===========================================================================


class TestCapabilityBoundary:
    def test_work_capability_registered(self, work_service: WorkService) -> None:
        registry = CapabilityRegistry()
        cap = WorkCapability(work_service)
        registry.register(cap)
        assert "work" in registry.list_capabilities()

    def test_work_capability_create(self, work_service: WorkService) -> None:
        cap = WorkCapability(work_service)
        resp = cap.invoke(
            Request(
                request_id="r1",
                payload={"action": "create", "objective": "Test via capability"},
            )
        )
        assert resp.success is True
        assert "work_id" in resp.data

    def test_work_capability_run_bounded(self, work_service: WorkService) -> None:
        cap = WorkCapability(work_service)
        create_resp = cap.invoke(
            Request(
                request_id="r1",
                payload={"action": "create", "objective": "Bounded via cap"},
            )
        )
        wid = create_resp.data["work_id"]
        resp = cap.invoke(
            Request(
                request_id="r2",
                payload={"action": "run_bounded", "work_id": wid, "max_steps": 3},
            )
        )
        assert resp.success is True
        assert resp.data["status"] in ("completed", "running")

    def test_work_capability_unknown_action(self, work_service: WorkService) -> None:
        cap = WorkCapability(work_service)
        resp = cap.invoke(
            Request(
                request_id="r1",
                payload={"action": "explode"},
            )
        )
        assert resp.success is False

    def test_no_orchestrator_dry_run(self, work_repo: SQLiteWorkRepository) -> None:
        svc = WorkService(repository=work_repo, orchestrator=None)
        work = svc.create_work("Dry run")
        plan = _make_plan(1)
        work = svc.set_plan(work.work_id, plan)
        work = svc.execute_next_step(work.work_id)
        assert work.plan is not None
        assert work.plan.steps[0].status == StepStatus.COMPLETED


# ===========================================================================
# 10. Status Transition Tests
# ===========================================================================


class TestStatusTransitions:
    def test_pause(self, work_service: WorkService) -> None:
        work = work_service.create_work("Pause me")
        work = work_service.auto_plan(work.work_id)
        work = work_service.pause_work(work.work_id)
        assert work.status == WorkStatus.PAUSED

    def test_cancel(self, work_service: WorkService) -> None:
        work = work_service.create_work("Cancel me")
        work = work_service.cancel_work(work.work_id)
        assert work.status == WorkStatus.CANCELLED

    def test_execute_non_ready_raises(self, work_service: WorkService) -> None:
        work = work_service.create_work("Not ready")
        with pytest.raises(ValueError, match="not executable"):
            work_service.execute_next_step(work.work_id)

    def test_run_bounded_invalid_max(self, work_service: WorkService) -> None:
        work = work_service.create_work("Bad max")
        with pytest.raises(ValueError, match="max_steps"):
            work_service.run_bounded(work.work_id, max_steps=0)
