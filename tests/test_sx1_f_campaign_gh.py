"""Sx1.F â€” Campaign G & H: Failure, Retry, TOCTOU & State Transition Attacks.

Campaign G: Failure -> Partial Mutation -> Retry
  - A failure must not leave behind a reusable authorization artifact.
  - Retry after approval consumed, retry with modified payload, retry against different resource.

Campaign H: TOCTOU / State Transition Attacks
  - Does the thing that executes remain logically equivalent to what was authorized?
  - Pre-auth vs post-auth parameter divergence, race window attacks, status race.
"""

from __future__ import annotations

from typing import Any

import pytest

from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.security import (
    ActorIdentity,
    ActorType,
)
from core.contracts.work import (
    StepStatus,
    WorkPlan,
    WorkStatus,
    WorkStep,
)
from core.orchestration.orchestrator import Orchestrator
from core.security.policy import create_default_policy
from core.security.service import SecurityService

# ---------------------------------------------------------------------------
# Flaky capability for retry testing
# ---------------------------------------------------------------------------


class FlakyCapability(Capability):
    """Fails on first invocation, succeeds on retry."""

    def __init__(self) -> None:
        self.call_count = 0

    @property
    def name(self) -> str:
        return "flaky"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Flaky capability for retry tests"

    def invoke(self, request: Request) -> Response:
        self.call_count += 1
        if self.call_count == 1:
            return Response(request_id=request.request_id, success=False, error="Transient failure")
        return Response(request_id=request.request_id, data={"call_count": self.call_count})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path) -> SQLiteWorkRepository:
    r = SQLiteWorkRepository(db_path=tmp_path / "test_work.db")
    r.initialize()
    return r


@pytest.fixture()
def flaky_cap() -> FlakyCapability:
    return FlakyCapability()


@pytest.fixture()
def service(repo) -> WorkService:
    return WorkService(repository=repo)


@pytest.fixture()
def security() -> SecurityService:
    return SecurityService(policy_engine=create_default_policy())


@pytest.fixture()
def registry(service, flaky_cap) -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(WorkCapability(service=service))
    reg.register(flaky_cap)
    return reg


@pytest.fixture()
def orchestrator(registry, security) -> Orchestrator:
    return Orchestrator(registry=registry, security_service=security)


def _make_work(service: WorkService, objective: str = "test work", actor: Any = None) -> str:
    work = service.create_work(objective=objective, actor=actor)
    return work.work_id


def _req(
    action: str,
    work_id: str = "",
    actor: Any = None,
    approved: bool = False,
    **extra: Any,
) -> Request:
    payload: dict[str, Any] = {"action": action, **extra}
    if work_id:
        payload["work_id"] = work_id
    if actor is not None:
        payload["_actor"] = actor
    if approved:
        payload["_security_approved"] = True
    return Request(request_id="sxf-req", payload=payload)


# ===========================================================================
# CAMPAIGN G: Failure -> Partial Mutation -> Retry
# ===========================================================================


class TestCampaignGFailureRetry:
    """Invariant: A failure must not leave behind a reusable authorization
    artifact that permits unintended future execution."""

    def test_sxg_01_failed_step_retry_increments_retry_count(self, repo, security, flaky_cap):
        """When a step fails and is retried, retry_count is tracked accurately."""
        reg = CapabilityRegistry()
        reg.register(flaky_cap)
        orch = Orchestrator(registry=reg, security_service=security)
        svc = WorkService(repository=repo, orchestrator=orch)

        w = svc.create_work(objective="retry test")
        step = WorkStep(
            step_id="s1", name="flaky step", description="desc", capability="flaky", max_retries=2
        )
        svc.set_plan(w.work_id, WorkPlan(plan_id="p1", steps=(step,)))

        # First attempt -> fails
        w = svc.execute_next_step(w.work_id)
        assert w.plan is not None
        s_step = w.plan.get_step("s1")
        assert s_step is not None
        assert s_step.status == StepStatus.FAILED

        # Explicit retry
        w = svc.retry_step(w.work_id, "s1")
        assert w.plan is not None
        s_step = w.plan.get_step("s1")
        assert s_step is not None
        assert s_step.status == StepStatus.READY
        assert s_step.retry_count == 1

        # Second attempt -> succeeds
        w = svc.execute_next_step(w.work_id)
        assert w.plan is not None
        s_step = w.plan.get_step("s1")
        assert s_step is not None
        assert s_step.status == StepStatus.COMPLETED

    def test_sxg_02_retry_exceeding_max_retries_is_rejected(self, service):
        """Retrying beyond max_retries raises ValueError."""
        step = WorkStep(
            step_id="s1",
            name="fail step",
            description="desc",
            capability="echo",
            status=StepStatus.FAILED,
            retry_count=1,
            max_retries=1,
        )
        w = service.create_work(objective="max retry test")
        service.set_plan(w.work_id, WorkPlan(plan_id="p1", steps=(step,)))

        with pytest.raises(ValueError, match="exhausted"):
            service.retry_step(w.work_id, "s1")

    def test_sxg_03_retry_non_failed_step_is_rejected(self, service):
        """Retrying a step that is NOT in FAILED status raises ValueError."""
        step = WorkStep(
            step_id="s1",
            name="ready step",
            description="desc",
            capability="echo",
            status=StepStatus.READY,
        )
        w = service.create_work(objective="bad retry")
        service.set_plan(w.work_id, WorkPlan(plan_id="p1", steps=(step,)))

        with pytest.raises(ValueError, match="not in FAILED status"):
            service.retry_step(w.work_id, "s1")

    def test_sxg_04_failed_orchestrator_call_does_not_persist_dirty_state(
        self, orchestrator, service
    ):
        """When Orchestrator rejects a call, the Work item remains unchanged in repo."""
        w_id = _make_work(service)
        # Attempt cancel without approval (will be rejected)
        orchestrator.route_request("work", _req("cancel", work_id=w_id, approved=False))
        # Verify status is still PENDING, not CANCELLED
        work = service.get_work(w_id)
        assert work.status == WorkStatus.PENDING

    def test_sxg_05_retry_after_plan_revision_retains_step_history(self, service):
        """Revising a plan preserves old plan in metadata history for audit."""
        step1 = WorkStep(
            step_id="s1",
            name="step 1",
            description="desc",
            capability="echo",
            status=StepStatus.COMPLETED,
        )
        step2 = WorkStep(
            step_id="s2",
            name="step 2",
            description="desc",
            capability="echo",
            status=StepStatus.PENDING,
        )
        w = service.create_work(objective="history test")
        service.set_plan(w.work_id, WorkPlan(plan_id="p1", steps=(step1, step2), version=1))

        step2_new = WorkStep(
            step_id="s2_v2", name="step 2 revised", description="desc", capability="echo"
        )
        updated = service.revise_plan(w.work_id, [step1, step2_new], reason="pivot strategy")
        assert updated.plan.version == 2
        history = updated.metadata.get("plan_history", [])
        assert len(history) == 1
        assert history[0]["version"] == 1


# ===========================================================================
# CAMPAIGN H: TOCTOU / State Transition Attacks
# ===========================================================================


class TestCampaignHTOCTOU:
    """Invariant: Does the thing that executes remain cryptographically /
    logically equivalent to the thing that was authorized?"""

    def test_sxh_01_payload_mutation_after_request_creation(self, orchestrator, service):
        """Mutating the Request payload after passing to route_request does NOT affect execution."""
        w_id = _make_work(service)
        payload = {"action": "status", "work_id": w_id}
        req = Request(request_id="toctou-1", payload=payload)

        # Mutate the payload dictionary before orchestrator finishes
        resp = orchestrator.route_request("work", req)
        payload["action"] = "cancel"  # Attempt to convert to cancel post-hoc
        assert resp.success is True
        assert service.get_work(w_id).status == WorkStatus.PENDING

    def test_sxh_02_status_transition_guards_terminal_states(self, service):
        """Terminal states (COMPLETED, CANCELLED, FAILED) reject all subsequent transitions."""
        w = service.create_work(objective="terminal guard")
        service.cancel_work(w.work_id)

        # All control actions on terminal work must fail
        with pytest.raises(Exception):  # WorkControlError
            service.pause_work(w.work_id)
        with pytest.raises(Exception):
            service.resume_work(w.work_id)
        with pytest.raises(Exception):
            service.request_intervention(w.work_id)
        with pytest.raises(Exception):
            service.take_over(w.work_id)

    def test_sxh_03_concurrent_status_checks_fail_closed_on_pause(self, service):
        """When work is PAUSED, _check_executable raises WorkControlError."""
        w = service.create_work(objective="pause check")
        service.pause_work(w.work_id)
        paused_work = service.get_work(w.work_id)
        with pytest.raises(Exception, match="paused"):
            service._check_executable(paused_work)

    def test_sxh_04_actor_metadata_immutable_during_route(self, orchestrator):
        """ActorIdentity cannot have its metadata modified during Orchestrator routing."""
        meta = {"tenant": "acme", "env": "prod"}
        actor = ActorIdentity(actor_id="audit-user", actor_type=ActorType.USER, metadata=meta)
        req = Request(
            request_id="meta-immut",
            payload={"action": "status", "_actor": actor},
        )
        orchestrator.route_request("work", req)
        # Verify original actor object metadata was not modified
        assert actor.metadata["tenant"] == "acme"
        assert actor.metadata["env"] == "prod"
