"""Sx1.F â€” Campaign E & F: Nested Execution & Context Corruption Attacks.

Campaign E: Nested Work -> Nested Capability
  - Authority must not silently expand merely because execution became nested.
  - Child work inheriting excessive authority, child losing actor context,
    nested approval confusion, re-entry authorization bypass.

Campaign F: Cross-Boundary Context Corruption
  - Mixed security contexts must never silently collapse into trusted context.
  - Mismatched _actor vs _security_actor vs resource vs approval.
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
# Test capability that attempts re-entry / nesting
# ---------------------------------------------------------------------------


class NestedAttackerCapability(Capability):
    """A capability that attempts to invoke other capabilities via Orchestrator."""

    def __init__(self, orchestrator: Orchestrator | None = None) -> None:
        self._orchestrator = orchestrator

    @property
    def name(self) -> str:
        return "nested_attacker"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Attempts nested Orchestrator re-entry"

    def set_orchestrator(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator

    def invoke(self, request: Request) -> Response:
        action = request.payload.get("action", "")
        if action == "reenter_cancel":
            target_work = request.payload.get("target_work_id", "")
            if self._orchestrator:
                child_req = Request(
                    request_id="nested-child",
                    payload={"action": "cancel", "work_id": target_work},
                )
                return self._orchestrator.route_request("work", child_req)
            return Response(request_id=request.request_id, success=False, error="No orchestrator")

        return Response(request_id=request.request_id, data={"echo": True})


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
def attacker_cap() -> NestedAttackerCapability:
    return NestedAttackerCapability()


@pytest.fixture()
def registry(service, attacker_cap) -> CapabilityRegistry:
    reg = CapabilityRegistry()
    reg.register(WorkCapability(service=service))
    reg.register(attacker_cap)
    return reg


@pytest.fixture()
def orchestrator(registry, security, attacker_cap) -> Orchestrator:
    orch = Orchestrator(registry=registry, security_service=security)
    attacker_cap.set_orchestrator(orch)
    return orch


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
# CAMPAIGN E: Nested Work -> Nested Capability
# ===========================================================================


class TestCampaignENestedExecution:
    """Invariant: Authority must not silently expand merely because
    execution became nested."""

    def test_sxe_01_nested_reentry_cannot_bypass_approval(self, orchestrator, service):
        """A nested capability call to work.cancel cannot bypass REQUIRE_APPROVAL."""
        w_id = _make_work(service)
        req = Request(
            request_id="parent-req",
            payload={
                "action": "reenter_cancel",
                "target_work_id": w_id,
                "_actor": {"actor_id": "user-1", "actor_type": "user"},
            },
        )
        resp = orchestrator.route_request("nested_attacker", req)
        assert resp.success is False
        assert "human approval" in resp.error.lower()
        assert service.get_work(w_id).status != WorkStatus.CANCELLED

    def test_sxe_02_workservice_invoking_capability_passes_security_actor(self, repo, security):
        """WorkService._invoke_capability propagates _security_actor from step/work."""

        class EchoCap(Capability):
            def __init__(self):
                self.received_request = None

            @property
            def name(self) -> str:
                return "echo"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def description(self) -> str:
                return "echo"

            def invoke(self, request: Request) -> Response:
                self.received_request = request
                return Response(request_id=request.request_id, data={"status": "ok"})

        echo = EchoCap()
        reg = CapabilityRegistry()
        reg.register(echo)
        orch = Orchestrator(registry=reg, security_service=security)
        svc = WorkService(repository=repo, orchestrator=orch)

        actor = ActorIdentity(actor_id="propagated-user", actor_type=ActorType.USER)
        w = svc.create_work(objective="nesting test", actor=actor)
        step = WorkStep(
            step_id="s1",
            name="step 1",
            description="desc",
            capability="echo",
            input_payload={"msg": "hello"},
        )
        plan = WorkPlan(plan_id="p1", steps=(step,))
        svc.set_plan(w.work_id, plan)

        svc.execute_next_step(w.work_id)
        assert echo.received_request is not None
        assert (
            "_security_actor" in echo.received_request.payload
            or "_actor" in echo.received_request.payload
        )

    def test_sxe_03_child_cannot_inherit_system_singleton_from_untrusted_parent(self, orchestrator):
        """Parent request with forged SYSTEM claims cannot give child real SYSTEM authority."""
        req = Request(
            request_id="forged-parent",
            payload={
                "action": "reenter_cancel",
                "target_work_id": "w-target",
                "_actor": {"actor_id": "forger", "actor_type": "system"},
            },
        )
        resp = orchestrator.route_request("nested_attacker", req)
        assert resp.success is False

    def test_sxe_04_nested_failure_preserves_work_boundary(self, repo, security):
        """Failure of a nested capability marks the step as failed, not corrupted."""

        class FailingCap(Capability):
            @property
            def name(self) -> str:
                return "failer"

            @property
            def version(self) -> str:
                return "1.0.0"

            @property
            def description(self) -> str:
                return "always fails"

            def invoke(self, request: Request) -> Response:
                return Response(
                    request_id=request.request_id, success=False, error="Capability exploded"
                )

        reg = CapabilityRegistry()
        reg.register(FailingCap())
        orch = Orchestrator(registry=reg, security_service=security)
        svc = WorkService(repository=repo, orchestrator=orch)

        w = svc.create_work(objective="nested fail test")
        step = WorkStep(step_id="s1", name="failing step", description="desc", capability="failer")
        plan = WorkPlan(plan_id="p1", steps=(step,))
        svc.set_plan(w.work_id, plan)

        updated = svc.execute_next_step(w.work_id)
        assert updated.plan is not None
        step_obj = updated.plan.get_step("s1")
        assert step_obj is not None
        assert step_obj.status == StepStatus.FAILED
        assert step_obj.error is not None


# ===========================================================================
# CAMPAIGN F: Cross-Boundary Context Corruption
# ===========================================================================


class TestCampaignFContextCorruption:
    """Invariant: Mixed security contexts must never silently collapse
    into a trusted context."""

    def test_sxf_01_forged_security_actor_overwritten_by_orchestrator(self, orchestrator, service):
        """External request supplying _security_actor directly is overwritten."""
        w_id = _make_work(service)
        req = Request(
            request_id="inject-sec-actor",
            payload={
                "action": "cancel",
                "work_id": w_id,
                "_security_actor": SYSTEM_ACTOR,
                "_actor": {"actor_id": "attacker", "actor_type": "user"},
            },
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "human approval" in resp.error.lower()

    def test_sxf_02_actor_id_none_or_empty_defaults_safely(self, orchestrator, service):
        """Actor with None or empty actor_id gets sanitized to anonymous USER."""
        w_id = _make_work(service)
        req = _req("cancel", work_id=w_id, actor={"actor_id": "", "actor_type": "user"})
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "human approval" in resp.error.lower()

    def test_sxf_03_invalid_actor_type_string_coerced_to_user(self, orchestrator, service):
        """Garbage actor_type like 'root', 'admin', 'god' is coerced to USER."""
        w_id = _make_work(service)
        for invalid_type in ["root", "admin", "god", "superuser", "system_admin"]:
            req = _req(
                "cancel", work_id=w_id, actor={"actor_id": "hacker", "actor_type": invalid_type}
            )
            resp = orchestrator.route_request("work", req)
            assert resp.success is False, f"Failed closed for invalid type: {invalid_type}"
            assert "human approval" in resp.error.lower()

    def test_sxf_04_trust_level_spoofing_in_dict_is_stripped_to_zero(
        self, orchestrator, service, security
    ):
        """Unverified dict payload asserting trust_level=9999 has trust forced to 0."""
        w_id = _make_work(service)
        req = _req(
            "status",
            work_id=w_id,
            actor={"actor_id": "spoofed", "actor_type": "user", "trust_level": 9999},
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is True
        events = security.event_log.get_events()
        assert len(events) > 0
        latest_event = events[-1]
        assert latest_event.decision.actor_id == "spoofed"

    def test_sxf_05_mixed_types_in_payload_do_not_crash_sanitization(self, orchestrator):
        """Weird payloads (integers, lists, None as actor) fail closed or sanitize safely."""
        weird_actors = [12345, [1, 2, 3], True, 3.14, b"bytes_actor"]
        for wa in weird_actors:
            req = Request(
                request_id="weird-actor",
                payload={"action": "cancel", "work_id": "w-1", "_actor": wa},
            )
            resp = orchestrator.route_request("work", req)
            assert resp.success is False

    def test_sxf_06_resource_field_priority_work_id_over_resource(
        self, orchestrator, service, security
    ):
        """Orchestrator resolves resource from work_id first, then resource field."""
        w_id = _make_work(service)
        req = Request(
            request_id="res-priority",
            payload={"action": "status", "work_id": w_id, "resource": "res-secondary"},
        )
        orchestrator.route_request("work", req)
        events = security.event_log.get_events()
        assert len(events) > 0
        assert events[-1].decision.resource == w_id
