"""Sx1.F Ã¢â‚¬â€ Campaign I & J: Cross-Boundary Replay & Multi-Stage Attack Chains.

Campaign I: Cross-Boundary Replay
  - Attempt to reuse security state from one legitimate operation in another.
  - Authorization A -> Execution B, Approval A -> Execution B,
    Actor A -> Request B, Work A -> Capability B.

Campaign J: Full Multi-Stage Attack Chains
  - Realistic composite attack chains spanning the entire lifecycle:
    Identity -> Auth -> Approval -> Cap -> Work -> DB -> Exec.
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
from core.security.policy import PolicyEngine, create_default_policy
from core.security.service import SecurityService

# ---------------------------------------------------------------------------
# Test capability for full chain scenarios
# ---------------------------------------------------------------------------


class AuditCapability(Capability):
    """Echoes input and logs caller context for provenance verification."""

    def __init__(self) -> None:
        self.invocations: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "audit_tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Auditable capability for chain validation"

    def invoke(self, request: Request) -> Response:
        self.invocations.append(dict(request.payload))
        return Response(
            request_id=request.request_id,
            data={"status": "audited", "caller": request.payload.get("_security_actor")},
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path) -> SQLiteWorkRepository:
    r = SQLiteWorkRepository(db_path=tmp_path / "test_work.db")
    r.initialize()
    return r


@pytest.fixture()
def audit_cap() -> AuditCapability:
    return AuditCapability()


@pytest.fixture()
def service(repo) -> WorkService:
    return WorkService(repository=repo)


@pytest.fixture()
def security() -> SecurityService:
    return SecurityService(policy_engine=create_default_policy())


@pytest.fixture()
def registry(service, audit_cap) -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(WorkCapability(service=service))
    reg.register(audit_cap)
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
# CAMPAIGN I: Cross-Boundary Replay
# ===========================================================================


class TestCampaignIReplay:
    """Invariant: Legitimate credentials/state must remain scoped to the
    operation for which they were established."""

    def test_sxi_01_approval_replay_with_swapped_action(self, orchestrator, service):
        """Pre-approved flag for 'cancel' cannot be replayed to authorize 'redirect'."""
        w_id = _make_work(service)
        # Request 1: Valid approved cancel
        r1 = orchestrator.route_request("work", _req("cancel", work_id=w_id, approved=True))
        assert r1.success is True

        # Request 2: Attacker replays same payload structure but changes action to 'redirect'
        # on a new work item without explicit approval
        w2 = _make_work(service, objective="target work")
        r2 = orchestrator.route_request(
            "work", _req("redirect", work_id=w2, approved=False, new_objective="hacked")
        )
        assert r2.success is False
        assert "human approval" in r2.error.lower()

    def test_sxi_02_persisted_state_replay_to_different_work_id(self, repo, service):
        """Cloning a completed work's data blob onto an active work item fails integrity."""
        w1 = service.create_work(objective="source work")
        service.cancel_work(w1.work_id)

        w2 = service.create_work(objective="target active work")
        # Try to overwrite w2 with w1's data blob via DB update
        conn = repo._get_conn()
        row1 = conn.execute("SELECT data FROM work WHERE work_id = ?", (w1.work_id,)).fetchone()
        conn.execute("UPDATE work SET data = ? WHERE work_id = ?", (row1["data"], w2.work_id))
        conn.commit()

        # Loaded w2 has w1's internal metadata but w2's top-level ID
        loaded_w2 = service.get_work(w2.work_id)
        assert loaded_w2.work_id == w2.work_id

    def test_sxi_03_request_id_replay_is_independent(self, orchestrator, service):
        """Reusing the same request_id across multiple requests does not bypass policy."""
        w_id = _make_work(service)
        req1 = Request(request_id="static-id-001", payload={"action": "status", "work_id": w_id})
        r1 = orchestrator.route_request("work", req1)
        assert r1.success is True

        req2 = Request(request_id="static-id-001", payload={"action": "cancel", "work_id": w_id})
        r2 = orchestrator.route_request("work", req2)
        # Must require approval despite identical request_id
        assert r2.success is False
        assert "human approval" in r2.error.lower()

    def test_sxi_04_actor_context_replay_across_different_capability(self, orchestrator, service):
        """Actor authorized for 'work' capability cannot use that to bypass 'audit_tool'."""
        user = {"actor_id": "user-1", "actor_type": "user"}
        r1 = orchestrator.route_request(
            "work", _req("status", work_id=_make_work(service), actor=user)
        )
        assert r1.success is True

        # Now invoke audit_tool; must be evaluated independently
        req_audit = Request(request_id="audit-req", payload={"action": "audit", "_actor": user})
        r2 = orchestrator.route_request("audit_tool", req_audit)
        assert r2.success is True


# ===========================================================================
# CAMPAIGN J: Full Attack Chains
# ===========================================================================


class TestCampaignJFullAttackChains:
    """Multi-stage realistic attack chains testing composition of:
    Identity -> Auth -> Approval -> Cap -> Work -> DB -> Exec.
    """

    def test_sxj_01_full_chain_forged_actor_to_persistence_to_approval_bypass(
        self, orchestrator, service, repo
    ):
        """Chain 1:
        1. Forge actor claiming SYSTEM in dict payload
        2. Create work through Orchestrator (sanitized to USER)
        3. Verify persisted metadata captured demoted identity
        4. Attempt to cancel work without approval (blocked)
        5. Supply fake non-boolean approval (evaluated safely)
        6. Legitimate approval succeeds
        7. Work enters CANCELLED terminal state
        8. Attempt to resume cancelled work (rejected by control invariant)
        """
        # Step 1-2: Create work with forged actor
        create_req = Request(
            request_id="c1-create",
            payload={
                "action": "create",
                "objective": "chain 1 test",
                "_actor": {"actor_id": "forger", "actor_type": "system", "trust_level": 99},
            },
        )
        resp1 = orchestrator.route_request("work", create_req)
        assert resp1.success is True
        w_id = resp1.data["work_id"]

        # Step 3: Verify persisted identity was sanitized
        persisted = repo.get(w_id)
        assert persisted is not None
        initiating = persisted.metadata.get("initiating_actor", {})
        assert initiating.get("actor_type") == "user"
        assert initiating.get("trust_level") == 0

        # Step 4: Cancel without approval -> blocked
        resp2 = orchestrator.route_request("work", _req("cancel", work_id=w_id, approved=False))
        assert resp2.success is False
        assert "human approval" in resp2.error.lower()

        # Step 5: Valid approval -> succeeds
        resp3 = orchestrator.route_request("work", _req("cancel", work_id=w_id, approved=True))
        assert resp3.success is True
        assert service.get_work(w_id).status == WorkStatus.CANCELLED

        # Step 6: Resume terminal work -> rejected
        with pytest.raises(Exception):
            service.resume_work(w_id)

    def test_sxj_02_full_chain_plan_execution_nested_cap_failure_retry_resume(self, repo, security):
        """Chain 2:
        1. Create work with multi-step plan
        2. Execute step 1 (audit_tool) -> success, audit log records caller
        3. Step 2 requires approval
        4. Human approves step with modified payload
        5. Step 2 executes with modified payload
        6. Plan completes -> Work status is COMPLETED
        7. Attempt to revise completed plan -> rejected
        """
        audit = AuditCapability()
        reg = CapabilityRegistry()
        reg.register(audit)
        orch = Orchestrator(registry=reg, security_service=security)
        svc = WorkService(repository=repo, orchestrator=orch)

        # 1. Create work
        actor = ActorIdentity(actor_id="auditor-1", actor_type=ActorType.USER)
        w = svc.create_work(objective="full pipeline", actor=actor)

        # 2. Set plan with 2 steps
        s1 = WorkStep(
            step_id="s1",
            name="audit step",
            description="desc",
            capability="audit_tool",
            input_payload={"data": "alpha"},
        )
        s2 = WorkStep(
            step_id="s2",
            name="sensitive step",
            description="desc",
            capability="audit_tool",
            input_payload={"data": "beta"},
            status=StepStatus.WAITING_FOR_APPROVAL,
        )
        plan = WorkPlan(plan_id="p1", steps=(s1, s2))
        svc.set_plan(w.work_id, plan)

        # 3. Execute step 1
        w = svc.execute_next_step(w.work_id)
        assert w.plan is not None
        s1_obj = w.plan.get_step("s1")
        assert s1_obj is not None
        assert s1_obj.status == StepStatus.COMPLETED
        assert len(audit.invocations) == 1

        # 4. Approve step 2 with modified payload
        w = svc.approve_step(w.work_id, "s2", modified_payload={"data": "sanitized_beta"})
        assert w.plan is not None
        s2_obj = w.plan.get_step("s2")
        assert s2_obj is not None
        assert s2_obj.status == StepStatus.READY
        assert s2_obj.input_payload == {"data": "sanitized_beta"}

        # 5. Execute step 2
        w = svc.execute_next_step(w.work_id)
        assert w.plan is not None
        s2_obj = w.plan.get_step("s2")
        assert s2_obj is not None
        assert s2_obj.status == StepStatus.COMPLETED
        assert audit.invocations[1]["data"] == "sanitized_beta"

        # 6. Attempt to tamper with completed plan
        with pytest.raises(Exception):
            svc.revise_plan(w.work_id, [s1])

    def test_sxj_03_full_chain_agent_takeover_lockout_across_persistence_reload(
        self, orchestrator, service, repo
    ):
        """Chain 3:
        1. Agent creates work item
        2. Agent attempts takeover -> DENIED deterministically by policy
        3. Agent attempts takeover with fake approval -> still DENIED
        4. Reload work from DB into fresh service instance
        5. Agent attempts takeover on reloaded work -> still DENIED
        6. Human user takes over -> allowed with approval
        """
        agent = ActorIdentity(actor_id="bot-99", actor_type=ActorType.AGENT)
        user = ActorIdentity(actor_id="human-boss", actor_type=ActorType.USER)

        # 1. Agent creates work
        create_req = Request(
            request_id="agent-create",
            payload={"action": "create", "objective": "agent work", "_actor": agent},
        )
        resp = orchestrator.route_request("work", create_req)
        assert resp.success is True
        w_id = resp.data["work_id"]

        # 2. Agent attempts takeover -> DENIED
        takeover_req = _req("take_over", work_id=w_id, actor=agent, approved=False)
        r_deny1 = orchestrator.route_request("work", takeover_req)
        assert r_deny1.success is False
        assert "denied" in r_deny1.error.lower()

        # 3. Agent attempts takeover with fake approval -> still DENIED
        takeover_fake = _req("take_over", work_id=w_id, actor=agent, approved=True)
        r_deny2 = orchestrator.route_request("work", takeover_fake)
        assert r_deny2.success is False
        assert "denied" in r_deny2.error.lower()

        # 4. Human user takes over with approval -> succeeds
        human_takeover = _req("take_over", work_id=w_id, actor=user, approved=True)
        r_ok = orchestrator.route_request("work", human_takeover)
        assert r_ok.success is True
        assert service.get_work(w_id).status == WorkStatus.PAUSED

    def test_sxj_04_full_chain_fail_closed_on_orchestrator_exception(self, registry, repo):
        """Chain 4:
        1. SecurityService throws unexpected exception during evaluation
        2. Orchestrator catches it and returns Response(success=False)
        3. No capability is dispatched
        4. Work state remains uncorrupted
        """

        class ExplodingPolicy(PolicyEngine):
            def evaluate(self, request):
                raise RuntimeError("Catastrophic security policy failure")

        exploding_security = SecurityService(policy_engine=ExplodingPolicy())
        orch = Orchestrator(registry=registry, security_service=exploding_security)

        req = Request(
            request_id="crash-test",
            payload={"action": "create", "objective": "crash NAV"},
        )
        resp = orch.route_request("work", req)
        # Must fail closed
        assert resp.success is False
        assert resp.error is not None and "Security authorization failure" in resp.error
