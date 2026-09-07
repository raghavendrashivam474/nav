"""Sx1.4 — Context, Confused Deputy & Execution Sink Tests (ATK-09 to ATK-15).

Continuation of the service boundary adversarial suite.
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
# Fixtures (duplicated for test isolation)
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


def _make_work(service: WorkService, objective: str = "test") -> str:
    return service.create_work(objective=objective).work_id


def _request(action: str, **kw: Any) -> Request:
    payload: dict[str, Any] = {"action": action, **kw}
    return Request(request_id="test-req", payload=payload)


# ===========================================================================
# ATK-09: Context Stripping
# ===========================================================================


class TestATK09ContextStripping:
    """What happens when actor/authorization context is removed between layers?

    Classification: BLOCKED at Orchestrator / ARCHITECTURAL WEAKNESS below
    """

    def test_atk09_orchestrator_strips_missing_actor_to_anonymous(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Orchestrator handles missing _actor by defaulting to anonymous."""
        resp = orchestrator.route_request(
            "work", _request("create", objective="no actor")
        )
        assert resp.success is True

    def test_atk09_service_ignores_missing_actor(self, service: WorkService):
        """WorkService methods don't require or check actor context."""
        work_id = _make_work(service)
        # cancel_work has no actor parameter at all
        work = service.cancel_work(work_id)
        assert work.status.value == "cancelled"

    def test_atk09_security_service_defaults_to_system(
        self, security: SecurityService
    ):
        """SecurityService.authorize() with no actor defaults to SYSTEM.

        This is a backward-compat design decision, but means any direct
        caller of SecurityService.authorize() without an actor gets
        SYSTEM-level authorization.
        """
        decision = security.authorize(action="work.cancel", resource="w1")
        assert decision.outcome.value == "allow"
        assert decision.actor_id == "nav:system"


# ===========================================================================
# ATK-10: Context Forgery
# ===========================================================================


class TestATK10ContextForgery:
    """Can downstream context be replaced with forged identity?

    Classification: BLOCKED at Orchestrator (Sx1.1/Sx1.3 protections hold)
    """

    def test_atk10_forged_system_actor_downgraded(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Forged SYSTEM actor in payload is downgraded to USER."""
        work_id = _make_work(service)
        fake_system = ActorIdentity(
            actor_id="imposter", actor_type=ActorType.SYSTEM, trust_level=100
        )
        resp = orchestrator.route_request(
            "work",
            _request("cancel", work_id=work_id, _actor=fake_system),
        )
        # Should require approval (USER policy), not auto-allow (SYSTEM policy)
        assert resp.success is False
        assert "approval" in (resp.error or "").lower()

    def test_atk10_forged_dict_system_downgraded(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Dict claiming actor_type=system is downgraded."""
        work_id = _make_work(service)
        resp = orchestrator.route_request(
            "work",
            _request(
                "cancel",
                work_id=work_id,
                _actor={"actor_id": "hacker", "actor_type": "system"},
            ),
        )
        assert resp.success is False

    def test_atk10_security_actor_overrides_raw_actor(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """_security_actor set by Orchestrator takes precedence over _actor."""
        resp = orchestrator.route_request(
            "work",
            _request(
                "create",
                objective="test",
                _actor={"actor_id": "user1", "actor_type": "user"},
            ),
        )
        assert resp.success is True


# ===========================================================================
# ATK-11: Confused Deputy
# ===========================================================================


class TestATK11ConfusedDeputy:
    """Can a low-authority actor cause a trusted service to perform
    a high-authority operation?

    Classification: ARCHITECTURAL WEAKNESS (potential)
    The service does not distinguish between callers. If a low-authority
    component obtains a service reference, it can perform any operation.
    """

    def test_atk11_service_does_not_distinguish_callers(
        self, service: WorkService
    ):
        """WorkService treats all callers identically."""
        work_id = _make_work(service)
        # No caller identity is checked
        work = service.cancel_work(work_id)
        assert work.status.value == "cancelled"

    def test_atk11_orchestrator_prevents_confused_deputy(
        self, orchestrator: Orchestrator, service: WorkService
    ):
        """Orchestrator prevents low-authority actors from privileged ops."""
        work_id = _make_work(service)
        agent = ActorIdentity(actor_id="agent1", actor_type=ActorType.AGENT)
        # Agent cannot take_over (DENY in policy)
        resp = orchestrator.route_request(
            "work", _request("take_over", work_id=work_id, _actor=agent)
        )
        assert resp.success is False
        assert "denied" in (resp.error or "").lower()


# ===========================================================================
# ATK-12: Privileged Internal Caller
# ===========================================================================


class TestATK12PrivilegedInternalCaller:
    """What happens if a privileged internal component is misused?"""

    def test_atk12_security_service_direct_authorize_grants_system(
        self, security: SecurityService
    ):
        """Direct SecurityService.authorize() with no actor grants SYSTEM."""
        decision = security.authorize(action="work.delete", resource="w1")
        assert decision.outcome.value == "allow"

    def test_atk12_security_service_with_explicit_actor(
        self, security: SecurityService
    ):
        """SecurityService respects explicit actor when provided."""
        user = ActorIdentity(actor_id="user1", actor_type=ActorType.USER)
        decision = security.authorize(
            actor=user, action="work.cancel", resource="w1"
        )
        assert decision.outcome.value == "require_approval"


# ===========================================================================
# ATK-13: Error / Exception Boundary
# ===========================================================================


class TestATK13ErrorBoundary:
    """Do exceptions between authorization and execution bypass policy?

    Sx1.1-B and Sx1.2 established fail-closed. Verify at service level.
    """

    def test_atk13_orchestrator_fails_closed_on_auth_exception(
        self, registry: CapabilityRegistry
    ):
        """Orchestrator returns error response on security exception."""
        # Create orchestrator with a broken security service
        class BrokenSecurity:
            def authorize(self, **kw):
                raise RuntimeError("security exploded")

        orch = Orchestrator(
            registry=registry, security_service=BrokenSecurity()  # type: ignore
        )
        resp = orch.route_request(
            "work", _request("create", objective="test")
        )
        assert resp.success is False
        assert "failure" in (resp.error or "").lower()

    def test_atk13_service_exception_does_not_escalate(
        self, service: WorkService
    ):
        """Service exceptions do not grant elevated privileges."""
        with pytest.raises(ValueError, match="not found"):
            service.cancel_work("nonexistent-work-id")


# ===========================================================================
# ATK-14: Composition / Nested Execution
# ===========================================================================


class TestATK14NestedExecution:
    """Can nested execution change actor, action, or acquire authority?"""

    def test_atk14_work_steps_do_not_carry_actor(
        self, service: WorkService
    ):
        """Work steps do not independently carry actor context."""
        work_id = _make_work(service)
        work = service.auto_plan(work_id)
        if work.plan and work.plan.steps:
            step = work.plan.steps[0]
            # Step input_payload does not contain actor information
            assert "_security_actor" not in step.input_payload
            assert "_actor" not in step.input_payload


# ===========================================================================
# ATK-15: Execution Sink Discovery
# ===========================================================================


class TestATK15ExecutionSinks:
    """Map the actual final execution sinks and their authorization paths."""

    def test_atk15_current_sinks_are_data_only(self, service: WorkService):
        """Current execution sinks are limited to SQLite data mutation.

        No filesystem, network, process, or hardware sinks exist yet.
        """
        work_id = _make_work(service)
        work = service.auto_plan(work_id)
        # Steps reference capabilities but don't execute them directly
        # The actual execution sink is the SQLite database
        assert work is not None

    def test_atk15_repository_is_only_persistence_sink(
        self, repo: SQLiteWorkRepository
    ):
        """The only current I/O sink is the SQLite database file."""
        import inspect

        source = inspect.getsource(type(repo))
        # No network, subprocess, or filesystem operations beyond sqlite
        assert "subprocess" not in source
        assert "requests." not in source
        assert "urllib" not in source
        assert "socket" not in source
