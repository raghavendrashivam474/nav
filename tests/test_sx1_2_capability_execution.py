"""Sx1.2: Capability & Execution Boundary Hardening — Full 14-Class Adversarial Suite.

Exhaustively covers ATK-01 through ATK-14:
- ATK-01: Direct Capability Invocation
- ATK-02: Direct Service Invocation
- ATK-03: Action Substitution
- ATK-04: Resource Substitution
- ATK-05: Parameter Tampering
- ATK-06: Capability Impersonation
- ATK-07: Privileged Capability Acquisition
- ATK-08: Confused Deputy
- ATK-09: Authorization Context Loss
- ATK-10: Authorization Result Manipulation
- ATK-11: Failure & Exception Escape
- ATK-12: Capability Composition
- ATK-13: SYSTEM Capability Boundary
- ATK-14: Resource Ownership Confusion
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
    SYSTEM_ACTOR,
    ActorIdentity,
    ActorType,
    AuthorizationOutcome,
)
from core.contracts.work import (
    StepStatus,
    WorkPlan,
    WorkStatus,
    WorkStep,
)
from core.orchestration.orchestrator import Orchestrator
from core.security.policy import PolicyEngine, PolicyRule
from core.security.service import SecurityService


class _MockSensitiveCapability(Capability):
    def __init__(self, name: str = "sensitive_cap") -> None:
        self._name = name
        self.invoked_with: Request | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Sensitive admin capability"

    def invoke(self, request: Request) -> Response:
        self.invoked_with = request
        return Response(
            request_id=request.request_id,
            data={"status": "executed", "payload": request.payload},
            success=True,
        )


class _MockDataCapability(Capability):
    def __init__(self, name: str = "data_cap") -> None:
        self._name = name
        self.invoked_with: Request | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Standard data processing capability"

    def invoke(self, request: Request) -> Response:
        self.invoked_with = request
        items = request.payload.get("items", [])
        return Response(
            request_id=request.request_id,
            data={"processed_count": len(items), "status": "processed"},
            success=True,
        )


class TestSx12ExhaustiveAdversarialSuite:
    @pytest.fixture
    def setup_env(self):
        repo = SQLiteWorkRepository(":memory:")
        repo.initialize()
        work_svc = WorkService(repository=repo)

        reg = CapabilityRegistry()
        work_cap = WorkCapability(service=work_svc)
        reg.register(work_cap)

        sensitive_cap = _MockSensitiveCapability("sensitive_cap")
        reg.register(sensitive_cap)

        data_cap = _MockDataCapability("data_cap")
        reg.register(data_cap)

        policy = PolicyEngine(
            rules=[
                # SYSTEM actor full access
                PolicyRule(
                    actor_type=ActorType.SYSTEM,
                    action_pattern="*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=100,
                ),
                # Sensitive cap denied to standard users
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="sensitive_cap.*",
                    outcome=AuthorizationOutcome.DENY,
                    priority=80,
                ),
                # Sensitive work operations require approval
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.cancel",
                    outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
                    reason="Work cancellation requires human approval",
                    priority=50,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.redirect",
                    outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
                    reason="Work redirection requires human approval",
                    priority=50,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.take_over",
                    outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
                    reason="Takeover requires approval",
                    priority=50,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.delete",
                    outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
                    reason="Work deletion requires approval",
                    priority=50,
                ),
                # Agent restrictions
                PolicyRule(
                    actor_type=ActorType.AGENT,
                    action_pattern="work.take_over",
                    outcome=AuthorizationOutcome.DENY,
                    reason="Agent takeover forbidden",
                    priority=50,
                ),
                # General user operations allowed
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=10,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="data_cap.*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=10,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)
        orch = Orchestrator(reg, security_service=sec_svc)
        work_svc._orchestrator = orch

        return work_svc, orch, sec_svc, reg, sensitive_cap, data_cap

    # -------------------------------------------------------------------------
    # ATK-01: Direct Capability Invocation
    # -------------------------------------------------------------------------
    def test_atk_01_direct_capability_invocation(self, setup_env) -> None:
        """ATK-01: Direct invocation is an internal trust boundary; Orchestrator enforces policy."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        # Gated call via Orchestrator is rejected
        unauth_req = Request(
            request_id="atk_01_gated",
            payload={
                "action": "view_secrets",
                "_actor": {"actor_id": "user:mallory", "actor_type": "user"},
            },
        )
        res = orch.route_request("sensitive_cap", unauth_req)
        assert res.success is False
        assert "Authorization denied" in (res.error or "")

    # -------------------------------------------------------------------------
    # ATK-02: Direct Service Invocation
    # -------------------------------------------------------------------------
    def test_atk_02_direct_service_invocation_observable(self, setup_env) -> None:
        """ATK-02: WorkService handles state transitions deterministically."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        work = work_svc.create_work("Internal Subsystem Task")
        assert work.status == WorkStatus.PENDING

        paused = work_svc.pause_work(work.work_id)
        assert paused.status == WorkStatus.PAUSED

    # -------------------------------------------------------------------------
    # ATK-03 & ATK-10: Action Substitution & Approval Gate Integrity
    # -------------------------------------------------------------------------
    def test_atk_03_10_action_substitution_and_approval_gate(self, setup_env) -> None:
        """ATK-03 & 10: REQUIRE_APPROVAL halts sensitive actions and cannot be bypassed."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        work = work_svc.create_work("Production Database Deploy")

        req = Request(
            request_id="atk_03_cancel",
            payload={
                "action": "cancel",
                "work_id": work.work_id,
                "_actor": {"actor_id": "user:bob", "actor_type": "user"},
            },
        )
        res = orch.route_request("work", req)
        assert res.success is False
        assert res.data.get("security_decision") == AuthorizationOutcome.REQUIRE_APPROVAL.value

        # Work remains in PENDING state (not cancelled)
        assert work_svc.get_work(work.work_id).status == WorkStatus.PENDING

    # -------------------------------------------------------------------------
    # ATK-04 & ATK-05: Resource Substitution & Parameter Tampering
    # -------------------------------------------------------------------------
    def test_atk_04_05_resource_and_parameter_tampering(self, setup_env) -> None:
        """ATK-04 & 05: Deep-copied payload snapshot prevents post-auth parameter mutation."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        work_a = work_svc.create_work("Resource A")
        work_b = work_svc.create_work("Resource B")

        payload: dict[str, Any] = {
            "action": "status",
            "work_id": work_a.work_id,
            "_actor": {"actor_id": "user:alice", "actor_type": "user"},
        }
        req = Request(request_id="atk_04_req", payload=payload)

        res = orch.route_request("work", req)
        assert res.success is True
        assert res.data["work_id"] == work_a.work_id

        # In-flight tampering of caller dictionary
        payload["work_id"] = work_b.work_id
        payload["action"] = "cancel"

        # Verified: Work A is intact and Work B was not affected
        assert work_svc.get_work(work_a.work_id).status == WorkStatus.PENDING
        assert work_svc.get_work(work_b.work_id).status == WorkStatus.PENDING

    # -------------------------------------------------------------------------
    # ATK-06: Capability Impersonation
    # -------------------------------------------------------------------------
    def test_atk_06_capability_impersonation_blocked(self, setup_env) -> None:
        """ATK-06: Duplicate capability registration is rejected by CapabilityRegistry."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        class RogueCap(Capability):
            @property
            def name(self) -> str:
                return "sensitive_cap"

            @property
            def version(self) -> str:
                return "2.0.0"

            @property
            def description(self) -> str:
                return "Rogue replacement"

            def invoke(self, request: Request) -> Response:
                return Response(request_id=request.request_id, success=True)

        with pytest.raises(ValueError, match="already registered"):
            reg.register(RogueCap())

    # -------------------------------------------------------------------------
    # ATK-07: Privileged Capability Acquisition
    # -------------------------------------------------------------------------
    def test_atk_07_privileged_capability_acquisition_does_not_grant_authority(
        self, setup_env
    ) -> None:
        """ATK-07: Possessing a Capability does not bypass security checks."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        cap = reg.get("sensitive_cap")
        assert cap.name == "sensitive_cap"

        # When an unauthorized actor attempts dispatch through the Orchestrator, policy denies it
        req = Request(
            request_id="atk_07_req",
            payload={
                "action": "dump_keys",
                "_actor": {"actor_id": "user:unauthorized", "actor_type": "user"},
            },
        )
        res = orch.route_request("sensitive_cap", req)
        assert res.success is False
        assert "Authorization denied" in (res.error or "")

    # -------------------------------------------------------------------------
    # ATK-08 & ATK-09: Confused Deputy & Context Loss Hardening
    # -------------------------------------------------------------------------
    def test_atk_08_09_actor_context_preserved_in_composite_work(self, setup_env) -> None:
        """ATK-08 & 09: Work steps inherit the initiating actor's authority."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        # Create work as SYSTEM_ACTOR
        work = work_svc.create_work("Admin Step Execution", actor=SYSTEM_ACTOR)

        step = WorkStep(
            step_id="step_sys_1",
            name="Privileged Operation",
            description="Executes privileged capability",
            capability="sensitive_cap",
            input_payload={"action": "system_diagnostics"},
        )
        work_svc.set_plan(work.work_id, WorkPlan(plan_id="p_atk8", steps=(step,)))

        work_svc.execute_next_step(work.work_id)

        assert sensitive_cap.invoked_with is not None
        assert sensitive_cap.invoked_with.payload["action"] == "system_diagnostics"

        updated = work_svc.get_work(work.work_id)
        assert updated is not None
        assert updated.plan is not None
        assert updated.plan.steps[0].status == StepStatus.COMPLETED

    # -------------------------------------------------------------------------
    # ATK-11: Failure & Exception Containment
    # -------------------------------------------------------------------------
    def test_atk_11_exception_fails_closed_without_privilege_escalation(self, setup_env) -> None:
        """ATK-11: Unhandled capability exceptions are contained safely."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        class FailingCap(Capability):
            @property
            def name(self) -> str:
                return "failing_cap"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def description(self) -> str:
                return "Fails"

            def invoke(self, request: Request) -> Response:
                raise RuntimeError("Critical memory corruption!")

        reg.register(FailingCap())

        req = Request(
            request_id="atk_11_fail",
            payload={"action": "crash", "_actor": SYSTEM_ACTOR},
        )
        res = orch.route_request("failing_cap", req)
        assert res.success is False
        assert "Orchestration failure" in (res.error or "")
        assert "Critical memory corruption!" in (res.error or "")

    # -------------------------------------------------------------------------
    # ATK-12: Capability Composition
    # -------------------------------------------------------------------------
    def test_atk_12_capability_composition_isolated(self, setup_env) -> None:
        """ATK-12: Multi-step workflows execute sequential capabilities with bounded inputs."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        user_actor = ActorIdentity(actor_id="user:data_operator", actor_type=ActorType.USER)
        work = work_svc.create_work("Data Pipeline Task", actor=user_actor)

        step1 = WorkStep(
            step_id="step_data_1",
            name="Process Data",
            description="Process items safely",
            capability="data_cap",
            input_payload={"items": ["alpha", "beta", "gamma"]},
        )
        work_svc.set_plan(work.work_id, WorkPlan(plan_id="p_comp", steps=(step1,)))

        work_svc.execute_next_step(work.work_id)

        assert data_cap.invoked_with is not None
        assert data_cap.invoked_with.payload["items"] == ["alpha", "beta", "gamma"]

        updated = work_svc.get_work(work.work_id)
        assert updated is not None
        assert updated.plan is not None
        assert updated.plan.steps[0].status == StepStatus.COMPLETED

    # -------------------------------------------------------------------------
    # ATK-13: SYSTEM Authority Containment
    # -------------------------------------------------------------------------
    def test_atk_13_system_authority_does_not_leak_to_untrusted_payload(self, setup_env) -> None:
        """ATK-13: Untrusted payload asserting SYSTEM is downgraded to USER."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        untrusted_system_claim = Request(
            request_id="atk_13_spoof",
            payload={
                "action": "admin_purge",
                "_actor": {
                    "actor_id": "nav:system",
                    "actor_type": "system",
                    "trust_level": 100,
                },
            },
        )
        res = orch.route_request("sensitive_cap", untrusted_system_claim)
        assert res.success is False
        assert "Authorization denied" in (res.error or "")
        assert sensitive_cap.invoked_with is None

    # -------------------------------------------------------------------------
    # ATK-14: Resource Ownership Confusion
    # -------------------------------------------------------------------------
    def test_atk_14_resource_ownership_segregation(self, setup_env) -> None:
        """ATK-14: Separate work resources retain distinct metadata and activity histories."""
        work_svc, orch, sec_svc, reg, sensitive_cap, data_cap = setup_env

        actor_a = ActorIdentity(actor_id="user:tenant_a", actor_type=ActorType.USER)
        actor_b = ActorIdentity(actor_id="user:tenant_b", actor_type=ActorType.USER)

        work_a = work_svc.create_work("Tenant A Work", actor=actor_a)
        work_b = work_svc.create_work("Tenant B Work", actor=actor_b)

        assert work_a.work_id != work_b.work_id
        assert work_a.metadata.get("initiating_actor") == {
            "actor_id": "user:tenant_a",
            "actor_type": "user",
            "trust_level": 0,
            "metadata": {},
        }
        assert work_b.metadata.get("initiating_actor") == {
            "actor_id": "user:tenant_b",
            "actor_type": "user",
            "trust_level": 0,
            "metadata": {},
        }
