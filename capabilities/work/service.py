"""Work execution service — S17.

Manages the full lifecycle of goal-directed work:
creation, planning, step-by-step execution, bounded loops,
failure handling, retries, and state inspection.

Key principles:
- Bounded execution (no infinite loops).
- Explicit checkpoints between steps.
- Failure is a first-class result.
- State is always inspectable.
- Capabilities invoked via Orchestrator, not direct imports.
- Activity logged at every meaningful transition.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from capabilities.work.evaluator import DeterministicEvaluator
from capabilities.work.planner import DeterministicPlanner
from capabilities.work.repository import WorkRepository
from core.contracts.capability import Request, Response
from core.contracts.context import NavContext
from core.contracts.work import (
    StepEvaluatorProtocol,
    StepStatus,
    Work,
    WorkActivity,
    WorkActivityType,
    WorkPlan,
    WorkQuery,
    WorkStatus,
    WorkStep,
)
from core.log import get_logger
from core.orchestration.orchestrator import Orchestrator

logger = get_logger(__name__)


class WorkService:
    """High-level work lifecycle management and bounded execution."""

    def __init__(
        self,
        repository: WorkRepository,
        orchestrator: Orchestrator | None = None,
        planner: DeterministicPlanner | None = None,
        evaluator: StepEvaluatorProtocol | None = None,
    ) -> None:
        self._repo = repository
        self._repo.initialize()
        self._orchestrator = orchestrator
        self._planner = planner or DeterministicPlanner()
        self._evaluator = evaluator or DeterministicEvaluator()

    # ------------------------------------------------------------------
    # Activity logging helper
    # ------------------------------------------------------------------

    @staticmethod
    def _record_activity(
        work: Work,
        activity_type: WorkActivityType,
        description: str = "",
        step_id: str | None = None,
        **meta: object,
    ) -> Work:
        now = datetime.now(timezone.utc).isoformat()
        entry = WorkActivity(
            timestamp=now,
            activity_type=activity_type,
            description=description,
            step_id=step_id,
            metadata={k: v for k, v in meta.items()},
        )
        return replace(
            work,
            activity_log=work.activity_log + (entry,),
            updated_at=now,
        )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def create_work(
        self,
        objective: str,
        tags: tuple[str, ...] = (),
        project_id: str | None = None,
        goal_id: str | None = None,
        investigation_id: str | None = None,
    ) -> Work:
        now = datetime.now(timezone.utc).isoformat()
        work = Work(
            work_id=f"work_{uuid.uuid4().hex[:12]}",
            objective=objective,
            status=WorkStatus.PENDING,
            project_id=project_id,
            goal_id=goal_id,
            investigation_id=investigation_id,
            tags=tags,
            created_at=now,
            updated_at=now,
        )
        work = self._record_activity(
            work, WorkActivityType.WORK_CREATED, description=objective
        )
        self._repo.save(work)
        logger.info("Created work %s: %s", work.work_id, objective)
        return work

    def create_from_context(
        self,
        context: NavContext,
        objective: str,
        tags: tuple[str, ...] = (),
    ) -> Work:
        project_id: str | None = None
        goal_id: str | None = None
        context_tags: list[str] = list(tags)

        pc = context.personal_context
        if pc is not None:
            focus = pc.current_focus
            if focus is not None:
                project_id = focus.project_id
                goal_id = focus.goal_id
                if focus.topic and focus.topic not in context_tags:
                    context_tags.append(focus.topic)

        return self.create_work(
            objective=objective,
            tags=tuple(context_tags),
            project_id=project_id,
            goal_id=goal_id,
        )

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def set_plan(self, work_id: str, plan: WorkPlan) -> Work:
        work = self._require(work_id)
        updated = replace(work, plan=plan, status=WorkStatus.READY)
        updated = self._record_activity(
            updated,
            WorkActivityType.PLAN_ESTABLISHED,
            description=f"Plan with {len(plan.steps)} steps",
        )
        self._repo.update(updated)
        logger.info("Plan set for work %s (%d steps)", work_id, len(plan.steps))
        return updated

    def auto_plan(self, work_id: str, context_hints: dict[str, Any] | None = None) -> Work:
        work = self._require(work_id)
        work = replace(work, status=WorkStatus.PLANNING)
        self._repo.update(work)

        plan = self._planner.create_plan(work.objective, context_hints)
        return self.set_plan(work_id, plan)

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    def execute_next_step(self, work_id: str) -> Work:
        work = self._require(work_id)

        if work.status not in (WorkStatus.READY, WorkStatus.RUNNING):
            raise ValueError(
                f"Work {work_id} is not executable (status={work.status.value})"
            )
        if work.plan is None:
            raise ValueError(f"Work {work_id} has no plan")

        ready = work.plan.ready_steps()

        if not ready:
            if work.plan.is_all_completed():
                return self._transition(work, WorkStatus.COMPLETED, "All steps completed")
            if work.plan.has_failed_step():
                return self._transition(work, WorkStatus.FAILED, "Unrecoverable step failure")
            return self._transition(work, WorkStatus.BLOCKED, "No ready steps available")

        step = ready[0]
        return self._execute_step(work, step)

    def _execute_step(self, work: Work, step: WorkStep) -> Work:
        now = datetime.now(timezone.utc).isoformat()

        # Mark step as RUNNING
        updated_step = replace(step, status=StepStatus.RUNNING, started_at=now)
        work = self._replace_step(work, step.step_id, updated_step)
        work = replace(work, status=WorkStatus.RUNNING, current_step_id=step.step_id)
        work = self._record_activity(
            work,
            WorkActivityType.STEP_STARTED,
            description=f"Executing: {step.name}",
            step_id=step.step_id,
        )
        self._repo.update(work)

        # Invoke capability via Orchestrator
        response = self._invoke_capability(step)

        # Evaluate result
        new_status, error_msg = self._evaluator.evaluate_step(
            step, response.data, response.success
        )

        completed_at = datetime.now(timezone.utc).isoformat()
        final_step = replace(
            updated_step,
            status=new_status,
            result=response.data,
            error=error_msg or response.error,
            completed_at=completed_at,
        )
        work = self._replace_step(work, step.step_id, final_step)

        if new_status == StepStatus.COMPLETED:
            work = self._record_activity(
                work,
                WorkActivityType.STEP_COMPLETED,
                description=f"Completed: {step.name}",
                step_id=step.step_id,
            )
        else:
            work = self._record_activity(
                work,
                WorkActivityType.STEP_FAILED,
                description=f"Failed: {step.name} — {error_msg}",
                step_id=step.step_id,
            )

        # Check overall completion
        if work.plan is not None and work.plan.is_all_completed():
            work = self._transition(work, WorkStatus.COMPLETED, "All steps completed")
        elif work.plan is not None and work.plan.has_failed_step():
            # Check if any failed step still has retries
            can_retry = any(
                s.status == StepStatus.FAILED and s.retry_count < s.max_retries
                for s in work.plan.steps
            )
            if not can_retry and not work.plan.ready_steps():
                work = self._transition(work, WorkStatus.FAILED, "Unrecoverable failure")
            else:
                work = replace(work, status=WorkStatus.RUNNING, updated_at=now)

        self._repo.update(work)
        return work

    def _invoke_capability(self, step: WorkStep) -> Response:
        if self._orchestrator is None:
            logger.warning("No orchestrator configured; returning mock success")
            return Response(
                request_id=f"req_{uuid.uuid4().hex[:8]}",
                data={"note": "No orchestrator; dry-run success"},
                success=True,
            )
        request = Request(
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            payload=step.input_payload,
        )
        return self._orchestrator.route_request(step.capability, request)

    # ------------------------------------------------------------------
    # Bounded execution
    # ------------------------------------------------------------------

    def run_bounded(self, work_id: str, max_steps: int = 5) -> Work:
        """Execute up to max_steps, stopping at terminal states."""
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")

        steps_executed = 0
        while steps_executed < max_steps:
            work = self._require(work_id)
            if work.status in (
                WorkStatus.COMPLETED,
                WorkStatus.FAILED,
                WorkStatus.CANCELLED,
                WorkStatus.PAUSED,
                WorkStatus.WAITING_FOR_INPUT,
                WorkStatus.BLOCKED,
            ):
                break
            if work.status == WorkStatus.PENDING:
                work = self.auto_plan(work_id)
            work = self.execute_next_step(work_id)
            steps_executed += 1

        return self._require(work_id)

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def retry_step(self, work_id: str, step_id: str) -> Work:
        work = self._require(work_id)
        if work.plan is None:
            raise ValueError(f"Work {work_id} has no plan")

        step = work.plan.get_step(step_id)
        if step is None:
            raise ValueError(f"Step {step_id} not found in work {work_id}")
        if step.status != StepStatus.FAILED:
            raise ValueError(f"Step {step_id} is not in FAILED status")
        if step.retry_count >= step.max_retries:
            raise ValueError(f"Step {step_id} has exhausted retries")

        retried = replace(
            step,
            status=StepStatus.READY,
            error=None,
            result={},
            retry_count=step.retry_count + 1,
            started_at=None,
            completed_at=None,
        )
        work = self._replace_step(work, step_id, retried)
        work = self._record_activity(
            work,
            WorkActivityType.STEP_RETRIED,
            description=f"Retry {retried.retry_count}/{retried.max_retries}",
            step_id=step_id,
        )
        if work.status == WorkStatus.FAILED:
            work = replace(work, status=WorkStatus.RUNNING)
        self._repo.update(work)
        return work

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def pause_work(self, work_id: str) -> Work:
        return self._transition(self._require(work_id), WorkStatus.PAUSED, "Paused by user")

    def cancel_work(self, work_id: str) -> Work:
        return self._transition(self._require(work_id), WorkStatus.CANCELLED, "Cancelled by user")

    def provide_input(self, work_id: str, input_data: dict[str, Any]) -> Work:
        work = self._require(work_id)
        if work.status != WorkStatus.WAITING_FOR_INPUT:
            raise ValueError(f"Work {work_id} is not waiting for input")
        work = self._record_activity(
            work,
            WorkActivityType.INPUT_PROVIDED,
            description="User provided input",
        )
        work = replace(work, status=WorkStatus.RUNNING)
        self._repo.update(work)
        return work

    def set_status(self, work_id: str, status: WorkStatus | str) -> Work:
        if isinstance(status, str):
            status = WorkStatus(status)
        return self._transition(self._require(work_id), status, f"-> {status.value}")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_work(self, work_id: str) -> Work | None:
        return self._repo.get(work_id)

    def list_work(self, query: WorkQuery | None = None) -> list[Work]:
        return self._repo.find(query or WorkQuery())

    def delete_work(self, work_id: str) -> bool:
        ok = self._repo.delete(work_id)
        if ok:
            logger.info("Deleted work %s", work_id)
        return ok

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require(self, work_id: str) -> Work:
        work = self._repo.get(work_id)
        if work is None:
            raise ValueError(f"Work {work_id} not found")
        return work

    def _transition(self, work: Work, status: WorkStatus, reason: str) -> Work:
        updated = replace(work, status=status)
        updated = self._record_activity(
            updated,
            WorkActivityType.STATUS_CHANGED,
            description=f"{status.value}: {reason}",
        )
        self._repo.update(updated)
        logger.info("Work %s -> %s (%s)", work.work_id, status.value, reason)
        return updated

    @staticmethod
    def _replace_step(work: Work, step_id: str, new_step: WorkStep) -> Work:
        if work.plan is None:
            return work
        new_steps = tuple(
            new_step if s.step_id == step_id else s for s in work.plan.steps
        )
        new_plan = replace(work.plan, steps=new_steps)
        return replace(work, plan=new_plan)
