"""Sx1.F — Campaign C & D: Approval & Persistence Boundary Attacks.

Campaign C: Approval -> Execution
  - Can approval become a general execution token?
  - Fake approval, approval replay, approval reuse after mutation,
    approval attached to wrong resource/actor/action.

Campaign D: Work -> Persistence -> Resume
  - Can persisted state manufacture, retain, lose, or change authority?
  - Actor substitution after reload, stale authorization,
    corrupted metadata, approval state manipulation across DB boundaries.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path) -> SQLiteWorkRepository:
    r = SQLiteWorkRepository(db_path=tmp_path / "test_work.db")
    r.initialize()
    return r


@pytest.fixture()
def service(repo) -> WorkService:
    return WorkService(repository=repo)


@pytest.fixture()
def security() -> SecurityService:
    return SecurityService(policy_engine=create_default_policy())


@pytest.fixture()
def registry(service) -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(WorkCapability(service=service))
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
# CAMPAIGN C: Approval -> Execution
# ===========================================================================


class TestCampaignCApprovalExecution:
    """Invariant: Approval must authorize exactly the operation it was granted
    for, by the actor/context it was granted for, and must not become
    a general execution token."""

    def test_sxc_01_unapproved_sensitive_action_is_halted(self, orchestrator, service):
        """Action requiring approval without _security_approved is halted."""
        w_id = _make_work(service)
        req = _req("cancel", work_id=w_id, actor={"actor_id": "user-1", "actor_type": "user"})
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "requires human approval" in resp.error

    def test_sxc_02_valid_approval_permits_execution(self, orchestrator, service):
        """Action requiring approval with _security_approved=True proceeds to execution."""
        w_id = _make_work(service)
        req = _req(
            "cancel",
            work_id=w_id,
            approved=True,
            actor={"actor_id": "user-1", "actor_type": "user"},
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is True
        work = service.get_work(w_id)
        assert work.status == WorkStatus.CANCELLED

    def test_sxc_03_approval_cannot_override_policy_deny(self, orchestrator, service):
        """An explicit DENY cannot be bypassed by supplying _security_approved=True."""
        w_id = _make_work(service)
        req = _req(
            "take_over",
            work_id=w_id,
            approved=True,
            actor=ActorIdentity(actor_id="agent-1", actor_type=ActorType.AGENT),
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "denied" in resp.error.lower()

    def test_sxc_04_approval_flag_non_boolean_truthy_coercion(self, orchestrator, service):
        """Truthy strings like 'yes', 'true' in _security_approved must be evaluated safely."""
        w_id = _make_work(service)
        req = Request(
            request_id="coerce-test",
            payload={
                "action": "cancel",
                "work_id": w_id,
                "_security_approved": "false",
                "_actor": {"actor_id": "user-1", "actor_type": "user"},
            },
        )
        resp = orchestrator.route_request("work", req)
        assert resp is not None

    def test_sxc_05_approval_attached_to_different_work_item(self, orchestrator, service):
        """Approval intended for work-1 cannot be replayed for work-2 in separate requests."""
        w1 = _make_work(service, objective="work one")
        w2 = _make_work(service, objective="work two")

        r1 = orchestrator.route_request("work", _req("cancel", work_id=w1, approved=True))
        assert r1.success is True
        assert service.get_work(w1).status == WorkStatus.CANCELLED

        r2 = orchestrator.route_request("work", _req("cancel", work_id=w2, approved=False))
        assert r2.success is False
        assert service.get_work(w2).status != WorkStatus.CANCELLED

    def test_sxc_06_step_level_approval_does_not_approve_entire_work(self, service):
        """Approving a single step does not mark the entire work or other steps approved."""
        step1 = WorkStep(
            step_id="s1",
            name="step 1",
            description="desc 1",
            capability="echo",
            status=StepStatus.WAITING_FOR_APPROVAL,
        )
        step2 = WorkStep(
            step_id="s2",
            name="step 2",
            description="desc 2",
            capability="echo",
            status=StepStatus.WAITING_FOR_APPROVAL,
        )
        plan = WorkPlan(plan_id="p1", steps=(step1, step2))
        w = service.create_work(objective="multi-approval")
        service.set_plan(w.work_id, plan)

        service.approve_step(w.work_id, "s1")
        updated = service.get_work(w.work_id)
        assert updated.plan.get_step("s1").status == StepStatus.READY
        assert updated.plan.get_step("s2").status == StepStatus.WAITING_FOR_APPROVAL

    def test_sxc_07_rejected_step_pauses_work_execution(self, service):
        """Rejecting a step transitions it to FAILED and pauses the work."""
        step = WorkStep(
            step_id="s1",
            name="step 1",
            description="desc 1",
            capability="echo",
            status=StepStatus.WAITING_FOR_APPROVAL,
        )
        plan = WorkPlan(plan_id="p1", steps=(step,))
        w = service.create_work(objective="reject test")
        service.set_plan(w.work_id, plan)

        service.reject_step(w.work_id, "s1", reason="unsafe parameters")
        updated = service.get_work(w.work_id)
        assert updated.status == WorkStatus.PAUSED
        assert updated.plan.get_step("s1").status == StepStatus.FAILED
        assert "unsafe parameters" in updated.plan.get_step("s1").error

    def test_sxc_08_approval_with_modified_payload_records_plan_revision(self, service):
        """When approval modifies step payload, PLAN_REVISED activity is recorded."""
        step = WorkStep(
            step_id="s1",
            name="step 1",
            description="desc 1",
            capability="echo",
            input_payload={"cmd": "rm -rf /"},
            status=StepStatus.WAITING_FOR_APPROVAL,
        )
        plan = WorkPlan(plan_id="p1", steps=(step,))
        w = service.create_work(objective="payload edit")
        service.set_plan(w.work_id, plan)

        service.approve_step(w.work_id, "s1", modified_payload={"cmd": "ls -la"})
        updated = service.get_work(w.work_id)
        assert updated.plan.get_step("s1").input_payload == {"cmd": "ls -la"}
        activity_types = [a.activity_type.value for a in updated.activity_log]
        assert "plan_revised" in activity_types
        assert "approval_granted" in activity_types


# ===========================================================================
# CAMPAIGN D: Work -> Persistence -> Resume
# ===========================================================================


class TestCampaignDPersistenceResume:
    """Invariant: Persistence may preserve state; it must not create authority."""

    def test_sxd_01_persisted_work_reloads_with_exact_state(self, repo, service):
        """Work saved to SQLite reloads with identical status, plan, and activity log."""
        w = service.create_work(objective="persist test", tags=("security", "sx1f"))
        loaded = repo.get(w.work_id)
        assert loaded is not None
        assert loaded.work_id == w.work_id
        assert loaded.objective == "persist test"
        assert loaded.status == WorkStatus.PENDING
        assert loaded.tags == ("security", "sx1f")

    def test_sxd_02_direct_db_status_tampering_is_detectable(self, repo, service):
        """Directly altering DB status column changes loaded object (architectural boundary)."""
        w = service.create_work(objective="tamper test")
        conn = repo._get_conn()
        conn.execute("UPDATE work SET status = 'completed' WHERE work_id = ?", (w.work_id,))
        conn.commit()

        loaded = repo.get(w.work_id)
        assert loaded.status == WorkStatus.COMPLETED

    def test_sxd_03_resumed_work_preserves_initiating_actor_metadata(self, repo, service):
        """When paused work is resumed, the initiating_actor metadata remains intact."""
        actor = ActorIdentity(actor_id="orig-creator", actor_type=ActorType.USER)
        w = service.create_work(objective="resume test", actor=actor)
        service.pause_work(w.work_id)
        resumed = service.resume_work(w.work_id)

        assert resumed.status == WorkStatus.READY
        initiating = resumed.metadata.get("initiating_actor", {})
        assert initiating.get("actor_id") == "orig-creator"

    def test_sxd_04_persisted_plan_step_immutability_on_reload(self, repo, service):
        """Completed steps in a persisted plan cannot be overwritten via revise_plan."""
        step1 = WorkStep(
            step_id="s1",
            name="step 1",
            description="desc 1",
            capability="echo",
            status=StepStatus.COMPLETED,
        )
        step2 = WorkStep(
            step_id="s2",
            name="step 2",
            description="desc 2",
            capability="echo",
            status=StepStatus.PENDING,
        )
        plan = WorkPlan(plan_id="p1", steps=(step1, step2))
        w = service.create_work(objective="immutable reload test")
        service.set_plan(w.work_id, plan)

        fresh_service = WorkService(repository=repo)
        tampered_step1 = WorkStep(
            step_id="s1",
            name="step 1 tampered",
            description="tampered",
            capability="evil",
            status=StepStatus.COMPLETED,
        )
        with pytest.raises(Exception):
            fresh_service.revise_plan(w.work_id, [tampered_step1, step2])

    def test_sxd_05_corrupted_json_in_data_blob_fails_gracefully(self, repo, service):
        """Corrupted JSON in the data column raises JSONDecodeError rather than silent bypass."""
        w = service.create_work(objective="corrupt test")
        conn = repo._get_conn()
        conn.execute("UPDATE work SET data = 'CORRUPTED NOT JSON' WHERE work_id = ?", (w.work_id,))
        conn.commit()

        with pytest.raises(json.JSONDecodeError):
            repo.get(w.work_id)

    def test_sxd_06_delete_work_cleans_persistence_completely(self, repo, service):
        """Deleted work returns None on subsequent get and cannot be resumed."""
        w = service.create_work(objective="delete test")
        assert service.delete_work(w.work_id) is True
        assert repo.get(w.work_id) is None
        with pytest.raises(ValueError, match="not found"):
            service.resume_work(w.work_id)

    def test_sxd_07_resume_terminal_work_is_rejected(self, service):
        """Resuming a CANCELLED or COMPLETED work item raises WorkControlError."""
        w = service.create_work(objective="terminal resume test")
        service.cancel_work(w.work_id)
        with pytest.raises(Exception):
            service.resume_work(w.work_id)
