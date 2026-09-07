"""Sx1.4 — Service & Execution Boundary Adversarial Tests.

Investigates whether NAV's internal service and execution surfaces
can cause privileged behavior without passing through the Orchestrator
security boundary.

Each test class maps to an ATK family from the Sx1.4 specification.
Tests classify findings as:
  CONFIRMED VULNERABILITY / ARCHITECTURAL WEAKNESS / BLOCKED / NOT APPLICABLE
"""

from __future__ import annotations

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
from core.orchestration.orchestrator import Orchestrator
from core.security.policy import create_default_policy
from core.security.service import SecurityService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path) -> SQLiteWorkRepository:
    """Fresh in-memory-ish SQLite repo per test."""
    r = SQLiteWorkRepository(db_path=tmp_path / "test_work.db")
    r.initialize()
    return r


@pytest.fixture()
def service(repo) -> WorkService:
    """WorkService wired to a fresh repo."""
    return WorkService(repository=repo)


@pytest.fixture()
def security() -> SecurityService:
    """Default SecurityService with standard policy."""
    return SecurityService(policy_engine=create_default_policy())


@pytest.fixture()
def registry(service) -> CapabilityRegistry:
    """Registry with WorkCapability registered."""
    reg = CapabilityRegistry()
    reg.register(WorkCapability(service=service))
    return reg


@pytest.fixture()
def orchestrator(registry, security) -> Orchestrator:
    """Fully wired Orchestrator with security."""
    return Orchestrator(registry=registry, security_service=security)


def _make_work(service: WorkService, objective: str = "test work") -> str:
    """Helper: create a work item and return its ID."""
    work = service.create_work(objective=objective)
    return work.work_id


def _request(
    action: str,
    work_id: str = "",
    actor: Any = None,
    approved: bool = False,
    **extra: Any,
) -> Request:
    """Build a Request payload mimicking external input."""
    payload: dict[str, Any] = {"action": action, **extra}
    if work_id:
        payload["work_id"] = work_id
    if actor is not None:
        payload["_actor"] = actor
    if approved:
        payload["_security_approved"] = True
    return Request(request_id="test-req", payload=payload)


# ===========================================================================
# ATK-01: Direct Service Invocation
# ===========================================================================


class TestATK01DirectServiceInvocation:
    """Can WorkService be directly invoked to perform privileged operations
    without Orchestrator authorization?

    Classification: ARCHITECTURAL WEAKNESS
    The service has no authorization checks. In the current in-process
    deployment model, no external attacker can obtain a WorkService
    reference. But any internal code path with a reference can bypass
    all policy.
    """

    def test_atk01_direct_cancel_without_authorization(self, service: WorkService):
        """Direct service cancel bypasses REQUIRE_APPROVAL policy."""
        work_id = _make_work(service)
        # Orchestrator would REQUIRE_APPROVAL for user cancel.
        # Direct service call has no such check.
        work = service.cancel_work(work_id)
        assert work.status.value == "cancelled"
        # FINDING: Cancel succeeded without any authorization or approval.

    def test_atk01_direct_delete_without_authorization(self, service: WorkService):
        """Direct service delete bypasses REQUIRE_APPROVAL policy."""
        work_id = _make_work(service)
        result = service.delete_work(work_id)
        assert result is True
        assert service.get_work(work_id) is None

    def test_atk01_direct_take_over_without_authorization(self, service: WorkService):
        """Direct service take_over bypasses REQUIRE_APPROVAL policy."""
        work_id = _make_work(service)
        work = service.take_over(work_id, reason="hostile takeover")
        assert work.status.value == "paused"

    def test_atk01_direct_redirect_without_authorization(self, service: WorkService):
        """Direct service redirect bypasses REQUIRE_APPROVAL policy."""
        work_id = _make_work(service)
        work = service.redirect_work(work_id, new_objective="pwned")
        assert work.objective == "pwned"

    def test_atk01_orchestrator_blocks_unapproved_cancel(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Control: Orchestrator correctly blocks unapproved cancel."""
        work_id = _make_work(service)
        user_actor = ActorIdentity(actor_id="user1", actor_type=ActorType.USER)
        resp = orchestrator.route_request(
            "work", _request("cancel", work_id=work_id, actor=user_actor)
        )
        assert resp.success is False
        assert "approval" in (resp.error or "").lower()

    def test_atk01_orchestrator_allows_approved_cancel(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Control: Orchestrator allows cancel with approval flag."""
        work_id = _make_work(service)
        user_actor = ActorIdentity(actor_id="user1", actor_type=ActorType.USER)
        resp = orchestrator.route_request(
            "work",
            _request("cancel", work_id=work_id, actor=user_actor, approved=True),
        )
        assert resp.success is True


# ===========================================================================
# ATK-02: Direct Repository Manipulation
# ===========================================================================


class TestATK02DirectRepositoryManipulation:
    """Can direct repository access bypass service/capability policy?

    Classification: ARCHITECTURAL WEAKNESS
    The repository is a pure data layer with no authorization.
    In the current model, it is only reachable through WorkService.
    """

    def test_atk02_direct_repo_delete(self, repo: SQLiteWorkRepository, service: WorkService):
        """Direct repo delete removes work without any policy check."""
        work_id = _make_work(service)
        assert repo.get(work_id) is not None
        result = repo.delete(work_id)
        assert result is True
        assert repo.get(work_id) is None

    def test_atk02_direct_repo_status_mutation(
        self, repo: SQLiteWorkRepository, service: WorkService
    ):
        """Direct repo update can change work status arbitrarily."""
        work_id = _make_work(service)
        work = repo.get(work_id)
        assert work is not None
        from dataclasses import replace

        from core.contracts.work import WorkStatus

        mutated = replace(work, status=WorkStatus.CANCELLED)
        repo.update(mutated)
        reloaded = repo.get(work_id)
        assert reloaded is not None
        assert reloaded.status == WorkStatus.CANCELLED

    def test_atk02_repo_has_no_actor_awareness(self, repo: SQLiteWorkRepository):
        """Repository methods accept no actor/authorization parameters."""
        import inspect

        for method_name in ("save", "get", "find", "update", "delete"):
            method = getattr(repo, method_name)
            sig = inspect.signature(method)
            param_names = list(sig.parameters.keys())
            assert "actor" not in param_names
            assert "authorization" not in param_names


# ===========================================================================
# ATK-03: Capability -> Service Boundary Bypass
# ===========================================================================


class TestATK03CapabilityServiceBypass:
    """Can capabilities invoke services in ways that bypass the security boundary?

    Classification: BLOCKED (by Orchestrator pre-check)
    The capability layer does not re-authorize, but the Orchestrator
    has already authorized the request before it reaches the capability.
    """

    def test_atk03_capability_receives_sanitized_actor(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Capability receives _security_actor set by Orchestrator."""
        user_actor = ActorIdentity(actor_id="user1", actor_type=ActorType.USER)
        resp = orchestrator.route_request(
            "work",
            _request("create", actor=user_actor, objective="test"),
        )
        assert resp.success is True
        work_id = resp.data["work_id"]
        work = service.get_work(work_id)
        assert work is not None

    def test_atk03_direct_capability_invocation_skips_auth(
        self, registry: CapabilityRegistry, service: WorkService
    ):
        """Direct capability.invoke() bypasses Orchestrator authorization.

        Classification: ARCHITECTURAL WEAKNESS
        """
        work_id = _make_work(service)
        capability = registry.get("work")
        # Direct invoke with no _security_actor — capability doesn't check
        resp = capability.invoke(_request("cancel", work_id=work_id))
        assert resp.success is True
        work = service.get_work(work_id)
        assert work is not None
        assert work.status.value == "cancelled"


# ===========================================================================
# ATK-04: Service -> Capability Re-entry
# ===========================================================================


class TestATK04ServiceCapabilityReentry:
    """Can services invoke capabilities again without re-authorization?

    Classification: NOT APPLICABLE (current architecture)
    WorkService does not hold a reference to CapabilityRegistry and
    does not invoke capabilities directly. Step execution is handled
    externally.
    """

    def test_atk04_service_has_no_registry_reference(self, service: WorkService):
        """WorkService does not hold a CapabilityRegistry reference."""
        assert not hasattr(service, "_registry")
        assert not hasattr(service, "registry")
        assert not hasattr(service, "_capabilities")

    def test_atk04_service_cannot_invoke_capabilities(self, service: WorkService):
        """WorkService has no method to invoke other capabilities."""

        methods = [m for m in dir(service) if not m.startswith("_")]
        invoke_methods = [m for m in methods if "invoke" in m.lower()]
        assert len(invoke_methods) == 0


# ===========================================================================
# ATK-05: Authorization Boundary Skipping
# ===========================================================================


class TestATK05AuthorizationBoundarySkipping:
    """Identify paths from input to privileged execution that skip authorization.

    Classification: ARCHITECTURAL WEAKNESS
    The only authorized path is Orchestrator.route_request().
    All other paths (direct service, direct capability, direct repo)
    skip authorization entirely.
    """

    def test_atk05_path_map_orchestrator_is_authorized(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Path: Input -> Orchestrator -> Capability -> Service [AUTHORIZED]."""
        work_id = _make_work(service)
        user_actor = ActorIdentity(actor_id="user1", actor_type=ActorType.USER)
        # Unapproved cancel through Orchestrator is blocked
        resp = orchestrator.route_request(
            "work", _request("cancel", work_id=work_id, actor=user_actor)
        )
        assert resp.success is False

    def test_atk05_path_map_direct_service_unauthorized(self, service: WorkService):
        """Path: Input -> Service [UNAUTHORIZED]."""
        work_id = _make_work(service)
        # No authorization check exists in the service
        work = service.cancel_work(work_id)
        assert work.status.value == "cancelled"

    def test_atk05_path_map_direct_capability_unauthorized(
        self, registry: CapabilityRegistry, service: WorkService
    ):
        """Path: Input -> Capability -> Service [UNAUTHORIZED]."""
        work_id = _make_work(service)
        capability = registry.get("work")
        resp = capability.invoke(_request("take_over", work_id=work_id))
        assert resp.success is True


# ===========================================================================
# ATK-06: Alternate Execution Entry Points
# ===========================================================================


class TestATK06AlternateEntryPoints:
    """Do alternate execution paths preserve security assumptions?

    Investigating: resume, retry, redirect, set_status, approve_step, etc.
    """

    def test_atk06_direct_resume_bypasses_auth(self, service: WorkService):
        """Direct resume_work bypasses any authorization."""
        work_id = _make_work(service)
        service.pause_work(work_id)
        work = service.resume_work(work_id)
        assert work.status.value in ("ready", "running")

    def test_atk06_direct_set_status_bypasses_auth(self, service: WorkService):
        """Direct set_status can force any status transition."""
        work_id = _make_work(service)
        from core.contracts.work import WorkStatus

        work = service.set_status(work_id, WorkStatus.CANCELLED)
        assert work.status == WorkStatus.CANCELLED

    def test_atk06_direct_approve_step_bypasses_auth(self, service: WorkService):
        """Direct approve_step bypasses approval security boundary."""
        work_id = _make_work(service)
        work = service.auto_plan(work_id)
        if work.plan and work.plan.steps:
            step_id = work.plan.steps[0].step_id
            # Direct approval without any security check
            work = service.approve_step(work_id, step_id)
            assert work is not None


# ===========================================================================
# ATK-07: Lifecycle Bypass
# ===========================================================================


class TestATK07LifecycleBypass:
    """Can Work lifecycle operations be performed without their intended
    control/security path?

    Classification: ARCHITECTURAL WEAKNESS
    All lifecycle operations are accessible through WorkService without
    authorization. The Orchestrator is the only gate.
    """

    @pytest.mark.parametrize(
        "operation",
        ["pause", "resume", "cancel", "take_over", "return_control"],
    )
    def test_atk07_lifecycle_operations_unprotected(
        self, service: WorkService, operation: str
    ):
        """All lifecycle operations succeed without authorization."""
        work_id = _make_work(service)
        if operation == "pause":
            work = service.pause_work(work_id)
            assert work.status.value == "paused"
        elif operation == "resume":
            service.pause_work(work_id)
            work = service.resume_work(work_id)
            assert work.status.value in ("ready", "running")
        elif operation == "cancel":
            work = service.cancel_work(work_id)
            assert work.status.value == "cancelled"
        elif operation == "take_over":
            work = service.take_over(work_id)
            assert work.status.value == "paused"
        elif operation == "return_control":
            service.take_over(work_id)
            work = service.return_control(work_id)
            assert work.status.value in ("ready", "running")


# ===========================================================================
# ATK-08: Approval Boundary Bypass
# ===========================================================================


class TestATK08ApprovalBoundaryBypass:
    """Can REQUIRE_APPROVAL operations execute without approval?

    Sx1.2 fixed the Orchestrator-level escape. Sx1.4 verifies that
    lower-level paths cannot bypass it.

    Classification:
    - Through Orchestrator: BLOCKED (Sx1.2 fix holds)
    - Through direct service: ARCHITECTURAL WEAKNESS (no approval check)
    - Through direct capability: ARCHITECTURAL WEAKNESS (no approval check)
    """

    def test_atk08_orchestrator_blocks_unapproved_cancel(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Orchestrator correctly enforces REQUIRE_APPROVAL for cancel."""
        work_id = _make_work(service)
        user = ActorIdentity(actor_id="user1", actor_type=ActorType.USER)
        resp = orchestrator.route_request(
            "work", _request("cancel", work_id=work_id, actor=user)
        )
        assert resp.success is False
        assert "approval" in (resp.error or "").lower()
        # Verify work was NOT cancelled
        work = service.get_work(work_id)
        assert work is not None
        assert work.status.value != "cancelled"

    def test_atk08_direct_service_bypasses_approval(self, service: WorkService):
        """Direct service cancel ignores REQUIRE_APPROVAL entirely."""
        work_id = _make_work(service)
        work = service.cancel_work(work_id)
        assert work.status.value == "cancelled"
        # FINDING: No approval was required or checked.

    def test_atk08_direct_capability_bypasses_approval(
        self, registry: CapabilityRegistry, service: WorkService
    ):
        """Direct capability cancel ignores REQUIRE_APPROVAL entirely."""
        work_id = _make_work(service)
        capability = registry.get("work")
        resp = capability.invoke(_request("cancel", work_id=work_id))
        assert resp.success is True
        work = service.get_work(work_id)
        assert work is not None
        assert work.status.value == "cancelled"

    @pytest.mark.parametrize("action", ["cancel", "redirect", "take_over"])
    def test_atk08_all_approval_actions_bypassable_via_service(
        self, service: WorkService, action: str
    ):
        """All REQUIRE_APPROVAL actions are bypassable through direct service."""
        work_id = _make_work(service)
        if action == "cancel":
            service.cancel_work(work_id)
        elif action == "redirect":
            service.redirect_work(work_id, new_objective="bypassed")
        elif action == "take_over":
            service.take_over(work_id)
        # All succeeded without approval
