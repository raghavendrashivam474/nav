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

_TERMINAL = frozenset({WorkStatus.COMPLETED, WorkStatus.FAILED, WorkStatus.CANCELLED})
_WAITING = frozenset({WorkStatus.WAITING_FOR_INPUT, WorkStatus.WAITING_FOR_APPROVAL})


class WorkControlError(ValueError):
    """Raised when a human control action is invalid or blocked."""


class PlanRevisionError(ValueError):
    """Raised when a plan revision is invalid (e.g., mutating completed steps)."""


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

        self._check_executable(work)

        if work.plan is None:
            raise ValueError(f"Work {work_id} has no plan")

        # S18: honour pending intervention before starting a new step
        control = work.metadata.get("control", {})
        if control.get("pending"):
            work = self._transition(
                work, WorkStatus.PAUSED,
                f"Intervention pending: {control.get('reason', 'unspecified')}",
            )
            return work

        plan = work.plan
        if plan is None:
            raise ValueError(f"Work {work_id} has no plan")
        ready = plan.ready_steps()

        if not ready:
            if plan.is_all_completed():
                return self._transition(work, WorkStatus.COMPLETED, "All steps completed")
            if plan.has_failed_step():
                return self._transition(work, WorkStatus.FAILED, "Unrecoverable step failure")
            return self._transition(work, WorkStatus.BLOCKED, "No ready steps available")

        step = ready[0]
        return self._execute_step(work, step)

    def _execute_step(self, work: Work, step: WorkStep) -> Work:
        now = datetime.now(timezone.utc).isoformat()

        # S18: Human Approval Gate
        requires_approval = step.metadata.get("requires_approval", False)
        approval_decision = step.metadata.get("approval_decision")
        if requires_approval and approval_decision != "approved":
            waiting_step = replace(step, status=StepStatus.WAITING_FOR_APPROVAL)
            work = self._replace_step(work, step.step_id, waiting_step)
            work = replace(
                work,
                status=WorkStatus.WAITING_FOR_APPROVAL,
                current_step_id=step.step_id,
                updated_at=now,
            )
            work = self._record_activity(
                work,
                WorkActivityType.APPROVAL_REQUESTED,
                description=f"Approval required for step: {step.name}",
                step_id=step.step_id,
                capability=step.capability,
            )
            self._repo.update(work)
            logger.info("Work %s waiting for approval on step %s", work.work_id, step.step_id)
            return work

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
        """Execute up to max_steps, stopping at terminal/control states."""
        if max_steps < 1:
            raise ValueError("max_steps must be >= 1")

        steps_executed = 0
        while steps_executed < max_steps:
            work = self._require(work_id)
            if work.status in _TERMINAL or work.status in _WAITING:
                break
            if work.status in (WorkStatus.PAUSED, WorkStatus.BLOCKED):
                break
            if work.status == WorkStatus.PENDING:
                work = self.auto_plan(work_id)

            # S18: re-check after auto-plan
            work = self._require(work_id)
            if work.status not in (WorkStatus.READY, WorkStatus.RUNNING):
                break

            work = self.execute_next_step(work_id)
            steps_executed += 1

            # S18: post-step control check
            work = self._require(work_id)
            if work.status != WorkStatus.RUNNING:
                break

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
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(
                f"Cannot pause terminal work ({work.status.value})"
            )
        if work.status == WorkStatus.PAUSED:
            return work  # idempotent
        work = self._transition(work, WorkStatus.PAUSED, "Paused by user")
        work = self._record_activity(
            work, WorkActivityType.WORK_PAUSED, "Work paused by human",
        )
        self._repo.update(work)
        return work

    def cancel_work(self, work_id: str) -> Work:
        work = self._require(work_id)
        if work.status == WorkStatus.CANCELLED:
            return work  # idempotent
        if work.status in (WorkStatus.COMPLETED, WorkStatus.FAILED):
            raise WorkControlError(
                f"Cannot cancel {work.status.value} work"
            )
        work = self._transition(work, WorkStatus.CANCELLED, "Cancelled by user")
        work = self._record_activity(
            work, WorkActivityType.WORK_CANCELLED, "Work cancelled by human",
        )
        self._repo.update(work)
        return work

    def resume_work(self, work_id: str) -> Work:
        work = self._require(work_id)
        if work.status != WorkStatus.PAUSED:
            raise WorkControlError(
                f"Cannot resume work in status {work.status.value}"
            )
        # Clear pending intervention
        meta = dict(work.metadata)
        control = dict(meta.get("control", {}))
        control["pending"] = False
        meta["control"] = control
        work = replace(work, metadata=meta)
        # Determine target status
        if work.plan is not None and work.plan.ready_steps():
            target = WorkStatus.RUNNING
        else:
            target = WorkStatus.READY
        work = replace(work, status=target)
        work = self._record_activity(
            work, WorkActivityType.WORK_RESUMED, "Work resumed by human",
        )
        self._repo.update(work)
        logger.info("Work %s resumed -> %s", work.work_id, target.value)
        return work

    def request_intervention(self, work_id: str, reason: str = "") -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(
                f"Cannot intervene on terminal work ({work.status.value})"
            )
        meta = dict(work.metadata)
        control = dict(meta.get("control", {}))
        control["pending"] = True
        control["reason"] = reason
        control["requested_at"] = datetime.now(timezone.utc).isoformat()
        meta["control"] = control
        work = replace(work, metadata=meta)
        work = self._record_activity(
            work,
            WorkActivityType.INTERVENTION_REQUESTED,
            f"Intervention requested: {reason}",
        )
        self._repo.update(work)
        return work

    def revise_plan(
        self,
        work_id: str,
        new_steps: list[WorkStep] | tuple[WorkStep, ...],
        reason: str = "",
    ) -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(
                f"Cannot revise plan of terminal work ({work.status.value})"
            )
        if work.plan is None:
            raise ValueError(f"Work {work_id} has no plan to revise")

        old_plan = work.plan
        immutable_old = [
            s for s in old_plan.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.RUNNING)
        ]

        # Invariant: Completed, running, or skipped steps must not be removed, changed or reordered.
        if len(new_steps) < len(immutable_old):
            raise PlanRevisionError("New plan cannot omit completed/running steps")
        for i, old_step in enumerate(immutable_old):
            new_step = new_steps[i]
            if new_step.step_id != old_step.step_id:
                raise PlanRevisionError(
                    f"Step at index {i} must be immutable step {old_step.step_id}"
                )
            if new_step.status != old_step.status:
                raise PlanRevisionError(
                    f"Step {old_step.step_id} status cannot be mutated"
                )
            if new_step.capability != old_step.capability:
                raise PlanRevisionError(
                    f"Step {old_step.step_id} capability cannot be mutated"
                )
            if new_step.input_payload != old_step.input_payload:
                raise PlanRevisionError(
                    f"Step {old_step.step_id} input payload cannot be mutated"
                )

        # Snapshot old plan into history
        meta = dict(work.metadata)
        history = list(meta.get("plan_history", []))

        # Serialize old plan to dict
        from capabilities.work.sqlite_repo import _plan_to_dict
        history.append(_plan_to_dict(old_plan))
        meta["plan_history"] = history

        # Create new WorkPlan with incremented version
        now = datetime.now(timezone.utc).isoformat()
        revised_plan = WorkPlan(
            plan_id=old_plan.plan_id,
            steps=tuple(new_steps),
            version=old_plan.version + 1,
            created_at=old_plan.created_at,
            updated_at=now,
            metadata=old_plan.metadata,
        )

        # Transition work back to READY or RUNNING based on ready steps
        target_status = WorkStatus.RUNNING if revised_plan.ready_steps() else WorkStatus.READY

        updated = replace(
            work,
            plan=revised_plan,
            status=target_status,
            metadata=meta,
            updated_at=now,
        )
        updated = self._record_activity(
            updated,
            WorkActivityType.PLAN_REVISED,
            description=f"Plan revised to v{revised_plan.version}: {reason}",
            metadata={"version": revised_plan.version, "reason": reason},
        )
        self._repo.update(updated)
        logger.info(
            "Work %s plan revised to v%d", work_id, revised_plan.version
        )
        return updated

    def redirect_work(
        self,
        work_id: str,
        new_objective: str | None = None,
        new_steps: list[WorkStep] | tuple[WorkStep, ...] | None = None,
        reason: str = "",
    ) -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(
                f"Cannot redirect terminal work ({work.status.value})"
            )

        now = datetime.now(timezone.utc).isoformat()
        updated = work

        # 1. Update objective if provided
        if new_objective is not None and new_objective != work.objective:
            updated = replace(updated, objective=new_objective, updated_at=now)

        # 2. Revise plan if steps are provided
        if new_steps is not None:
            # Save our objective change first if any, so revise_plan sees it
            self._repo.update(updated)
            updated = self.revise_plan(work_id, new_steps, reason=reason)
            # Re-read to get latest state from revise_plan
            updated = self._require(work_id)

        # 3. Log redirection activity
        updated = self._record_activity(
            updated,
            WorkActivityType.WORK_REDIRECTED,
            description=f"Work redirected: {reason}",
            metadata={"reason": reason, "new_objective": new_objective},
        )
        self._repo.update(updated)
        logger.info("Work %s redirected", work_id)
        return updated

    def approve_step(
        self,
        work_id: str,
        step_id: str,
        modified_payload: dict[str, Any] | None = None,
    ) -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(f"Cannot approve step on terminal work ({work.status.value})")
        if work.plan is None:
            raise ValueError(f"Work {work_id} has no plan")
        step = work.plan.get_step(step_id)
        if step is None:
            raise ValueError(f"Step {step_id} not found in work {work_id}")

        meta = dict(step.metadata)
        meta["approval_decision"] = "approved"
        meta["approved_at"] = datetime.now(timezone.utc).isoformat()

        payload = modified_payload if modified_payload is not None else step.input_payload
        updated_step = replace(
            step,
            status=StepStatus.READY,
            input_payload=payload,
            metadata=meta,
        )
        work = self._replace_step(work, step_id, updated_step)
        work = replace(work, status=WorkStatus.RUNNING)

        if modified_payload is not None:
            work = self._record_activity(
                work,
                WorkActivityType.PLAN_REVISED,
                description=f"Modified parameters for approved step: {step.name}",
                step_id=step_id,
            )

        work = self._record_activity(
            work,
            WorkActivityType.APPROVAL_GRANTED,
            description=f"Approval granted for step: {step.name}",
            step_id=step_id,
        )
        self._repo.update(work)
        logger.info("Approved step %s for work %s", step_id, work_id)
        return work

    def reject_step(
        self,
        work_id: str,
        step_id: str,
        reason: str = "",
    ) -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(f"Cannot reject step on terminal work ({work.status.value})")
        if work.plan is None:
            raise ValueError(f"Work {work_id} has no plan")
        step = work.plan.get_step(step_id)
        if step is None:
            raise ValueError(f"Step {step_id} not found in work {work_id}")

        meta = dict(step.metadata)
        meta["approval_decision"] = "rejected"
        meta["rejected_at"] = datetime.now(timezone.utc).isoformat()
        meta["rejection_reason"] = reason

        err_msg = f"Rejected by human: {reason}" if reason else "Rejected by human"
        updated_step = replace(
            step,
            status=StepStatus.FAILED,
            error=err_msg,
            metadata=meta,
        )
        work = self._replace_step(work, step_id, updated_step)
        # Pause work so human can decide how to redirect or cancel
        work = replace(work, status=WorkStatus.PAUSED)
        work = self._record_activity(
            work,
            WorkActivityType.APPROVAL_REJECTED,
            description=f"Approval rejected for step {step.name}: {reason}",
            step_id=step_id,
            reason=reason,
        )
        self._repo.update(work)
        logger.info("Rejected step %s for work %s", step_id, work_id)
        return work

    def request_input(
        self,
        work_id: str,
        step_id: str | None = None,
        prompt: str = "",
    ) -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(f"Cannot request input on terminal work ({work.status.value})")

        if step_id and work.plan:
            step = work.plan.get_step(step_id)
            if step:
                updated_step = replace(step, status=StepStatus.WAITING_FOR_INPUT)
                work = self._replace_step(work, step_id, updated_step)

        work = replace(
            work,
            status=WorkStatus.WAITING_FOR_INPUT,
            current_step_id=step_id or work.current_step_id,
        )
        work = self._record_activity(
            work,
            WorkActivityType.INPUT_REQUESTED,
            description=prompt or "Input requested by system",
            step_id=step_id,
        )
        self._repo.update(work)
        return work

    def provide_input(
        self,
        work_id: str,
        input_data: dict[str, Any],
        step_id: str | None = None,
    ) -> Work:
        work = self._require(work_id)
        if work.status != WorkStatus.WAITING_FOR_INPUT:
            raise WorkControlError(f"Work {work_id} is not waiting for input")

        sid = step_id or work.current_step_id
        if sid and work.plan:
            step = work.plan.get_step(sid)
            if step and step.status == StepStatus.WAITING_FOR_INPUT:
                merged = {**step.input_payload, **input_data}
                updated_step = replace(step, status=StepStatus.READY, input_payload=merged)
                work = self._replace_step(work, sid, updated_step)

        work = replace(work, status=WorkStatus.RUNNING)
        work = self._record_activity(
            work,
            WorkActivityType.INPUT_PROVIDED,
            description="User provided input",
            step_id=sid,
            input_keys=list(input_data.keys()),
        )
        self._repo.update(work)
        return work

    def take_over(self, work_id: str, reason: str = "") -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(f"Cannot take over terminal work ({work.status.value})")

        work = replace(work, status=WorkStatus.PAUSED)
        work = self._record_activity(
            work,
            WorkActivityType.HUMAN_TAKEOVER,
            description=f"Human took over work: {reason}",
            reason=reason,
        )
        self._repo.update(work)
        logger.info("Human took over work %s", work_id)
        return work

    def return_control(self, work_id: str, reason: str = "") -> Work:
        work = self._require(work_id)
        if work.status in _TERMINAL:
            raise WorkControlError(f"Cannot return control on terminal work ({work.status.value})")

        target = WorkStatus.RUNNING if (work.plan and work.plan.ready_steps()) else WorkStatus.READY
        work = replace(work, status=target)
        work = self._record_activity(
            work,
            WorkActivityType.CONTROL_RETURNED,
            description=f"Control returned to NAV: {reason}",
            reason=reason,
        )
        self._repo.update(work)
        logger.info("Control returned to NAV for work %s", work_id)
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

    def _check_executable(self, work: Work) -> None:
        """Raise WorkControlError if work cannot advance."""
        if work.status in _TERMINAL:
            raise WorkControlError(
                f"Work {work.work_id} is terminal ({work.status.value})"
            )
        if work.status == WorkStatus.PAUSED:
            raise WorkControlError(
                f"Work {work.work_id} is paused — resume before executing"
            )
        if work.status in _WAITING:
            raise WorkControlError(
                f"Work {work.work_id} is waiting ({work.status.value})"
            )
        if work.status not in (WorkStatus.READY, WorkStatus.RUNNING):
            raise WorkControlError(
                f"Work {work.work_id} is not executable (status={work.status.value})"
            )

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
