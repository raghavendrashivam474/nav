"""Work contracts — S17: Technical Intelligence & Agentic Workflows.

Defines the core abstractions for goal-directed work, execution planning,
step execution, status tracking, bounded execution loops, and activity logs.

Follows the NAV principle:
Suggest, never silently substitute; bounded execution; explicit checkpoints.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkStatus(str, Enum):
    """Lifecycle state of a Work item."""

    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAITING_FOR_INPUT = "waiting_for_input"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Lifecycle state of an individual WorkStep."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_FOR_INPUT = "waiting_for_input"


class WorkActivityType(str, Enum):
    """Granular operational activity type for observability and continuity."""

    WORK_CREATED = "work_created"
    PLAN_PROPOSED = "plan_proposed"
    PLAN_ESTABLISHED = "plan_established"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRIED = "step_retried"
    EVALUATION_PERFORMED = "evaluation_performed"
    STATUS_CHANGED = "status_changed"
    INPUT_REQUESTED = "input_requested"
    INPUT_PROVIDED = "input_provided"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkStep:
    """A bounded atomic unit of work within a WorkPlan."""

    step_id: str
    name: str
    description: str
    capability: str
    input_payload: dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    dependencies: tuple[str, ...] = ()
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    max_retries: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkPlan:
    """A structured sequence or DAG of work steps toward a goal."""

    plan_id: str
    steps: tuple[WorkStep, ...] = ()
    version: int = 1
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step(self, step_id: str) -> WorkStep | None:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def ready_steps(self) -> tuple[WorkStep, ...]:
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        ready = []
        for s in self.steps:
            if s.status in (StepStatus.PENDING, StepStatus.READY):
                if all(dep in completed_ids for dep in s.dependencies):
                    ready.append(s)
        return tuple(ready)

    def is_all_completed(self) -> bool:
        if not self.steps:
            return False
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    def has_failed_step(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)


@dataclass(frozen=True)
class WorkActivity:
    """Structured activity log entry recording execution progress."""

    timestamp: str
    activity_type: WorkActivityType
    description: str = ""
    step_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Work:
    """Persistent, inspectable, goal-directed work unit."""

    work_id: str
    objective: str
    status: WorkStatus = WorkStatus.PENDING
    plan: WorkPlan | None = None
    current_step_id: str | None = None
    project_id: str | None = None
    goal_id: str | None = None
    investigation_id: str | None = None
    tags: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    activity_log: tuple[WorkActivity, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_current_step(self) -> WorkStep | None:
        if self.plan is None or self.current_step_id is None:
            return None
        return self.plan.get_step(self.current_step_id)

    def completed_steps(self) -> tuple[WorkStep, ...]:
        if self.plan is None:
            return ()
        return tuple(s for s in self.plan.steps if s.status == StepStatus.COMPLETED)

    def pending_steps(self) -> tuple[WorkStep, ...]:
        if self.plan is None:
            return ()
        return tuple(
            s for s in self.plan.steps if s.status in (StepStatus.PENDING, StepStatus.READY)
        )


@dataclass(frozen=True)
class WorkQuery:
    """Filter criteria for listing Work items."""

    query_text: str | None = None
    status: str | None = None
    project_id: str | None = None
    goal_id: str | None = None
    investigation_id: str | None = None
    tags: tuple[str, ...] = ()
    limit: int = 20


# ---------------------------------------------------------------------------
# Protocols / Interfaces
# ---------------------------------------------------------------------------


class PlannerProtocol(Protocol):
    """Protocol for constructing a WorkPlan from an objective and context."""

    def create_plan(
        self,
        objective: str,
        context_hints: dict[str, Any] | None = None,
    ) -> WorkPlan: ...


class StepEvaluatorProtocol(Protocol):
    """Protocol for evaluating step outputs and recommending next status."""

    def evaluate_step(
        self,
        step: WorkStep,
        result_payload: dict[str, Any],
        is_success: bool,
    ) -> tuple[StepStatus, str | None]: ...


class WorkCapabilityInterface(ABC):
    """Contract for the Work capability."""

    @abstractmethod
    def create_work(
        self,
        objective: str,
        tags: tuple[str, ...] = (),
        project_id: str | None = None,
        goal_id: str | None = None,
        investigation_id: str | None = None,
    ) -> Work:
        pass

    @abstractmethod
    def execute_next_step(self, work_id: str) -> Work:
        pass

    @abstractmethod
    def run_bounded(self, work_id: str, max_steps: int = 5) -> Work:
        pass
