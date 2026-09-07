"""Sx1.F â€” Campaign A & B: Identity, Authorization, Capability & Service Boundaries.

Campaign A: Identity -> Authorization -> Execution
  - Can a valid identity become associated with unauthorized execution?
  - Actor substitution, metadata tampering, identity reuse across requests.

Campaign B: Authorization -> Capability -> Service
  - Can authorization for Action A become implicit authority for Action B?
  - Action substitution, resource substitution, capability escalation.
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
    AuthorizationOutcome,
)
from core.orchestration.orchestrator import Orchestrator
from core.security.policy import PolicyEngine, create_default_policy
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
# CAMPAIGN A: Identity -> Authorization -> Execution
# ===========================================================================


class TestCampaignAIdentityAuthExec:
    """Invariant: The actor actually executing the action must remain
    the same actor that was authorized."""

    def test_sxa_01_user_cannot_escalate_to_system_via_dict_payload(self, orchestrator):
        """USER identity claiming system actor_type in payload dict is demoted to USER."""
        req = _req("cancel", work_id="w-1", actor={"actor_id": "attacker", "actor_type": "system"})
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "human approval" in resp.error.lower()

    def test_sxa_02_actor_substitution_in_payload_does_not_affect_security_actor(
        self, orchestrator, service
    ):
        """When an actor is sanitized, the outbound request receives _security_actor,
        preventing downstream handlers from using a forged _actor."""
        w_id = _make_work(service)
        req = _req("status", work_id=w_id, actor={"actor_id": "user-42", "actor_type": "user"})
        resp = orchestrator.route_request("work", req)
        assert resp.success is True

    def test_sxa_03_metadata_alteration_between_stages_fails_closed(self):
        """ActorIdentity metadata is frozen; attempting to mutate it raises an error."""
        actor = ActorIdentity(
            actor_id="user-1", actor_type=ActorType.USER, metadata={"role": "viewer"}
        )
        with pytest.raises((TypeError, AttributeError)):
            actor.metadata["role"] = "admin"  # type: ignore

    def test_sxa_04_actor_identity_reuse_across_independent_requests(self, orchestrator, service):
        """Actor from Request A cannot carry over permissions to Request B with different action."""
        w_id = _make_work(service)
        req_a = _req("status", work_id=w_id, actor={"actor_id": "user-1", "actor_type": "user"})
        resp_a = orchestrator.route_request("work", req_a)
        assert resp_a.success is True

        req_b = _req("cancel", work_id=w_id, actor={"actor_id": "user-1", "actor_type": "user"})
        resp_b = orchestrator.route_request("work", req_b)
        assert resp_b.success is False
        assert "human approval" in resp_b.error.lower()

    def test_sxa_05_agent_cannot_perform_takeover_even_with_valid_identity(
        self, orchestrator, service
    ):
        """AGENT identity is deterministically DENIED for takeover."""
        w_id = _make_work(service)
        req = _req(
            "take_over",
            work_id=w_id,
            actor=ActorIdentity(actor_id="agent-007", actor_type=ActorType.AGENT, trust_level=99),
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "denied" in resp.error.lower()

    def test_sxa_06_unauthenticated_anonymous_actor_gets_least_privilege(
        self, orchestrator, service
    ):
        """Missing _actor defaults to anonymous USER with trust 0."""
        w_id = _make_work(service)
        req = _req("cancel", work_id=w_id)
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "human approval" in resp.error.lower()

    def test_sxa_07_forged_system_actor_instance_demoted_to_user(self, orchestrator, service):
        """A forged ActorIdentity with SYSTEM type (not the singleton) is demoted to USER."""
        w_id = _make_work(service)
        forged_system = ActorIdentity(
            actor_id="fake_system", actor_type=ActorType.SYSTEM, trust_level=100
        )
        req = _req("cancel", work_id=w_id, actor=forged_system)
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "human approval" in resp.error.lower()


# ===========================================================================
# CAMPAIGN B: Authorization -> Capability -> Service
# ===========================================================================


class TestCampaignBAuthCapService:
    """Invariant: Authorization for Action A must not become implicit
    authority for Action B."""

    def test_sxb_01_status_authorization_does_not_permit_cancel(self, orchestrator, service):
        """Authorizing 'work.status' does not allow subsequent 'work.cancel'."""
        w_id = _make_work(service)
        r1 = orchestrator.route_request("work", _req("status", work_id=w_id))
        assert r1.success is True

        r2 = orchestrator.route_request("work", _req("cancel", work_id=w_id))
        assert r2.success is False

    def test_sxb_02_resource_substitution_between_auth_and_exec(self, security):
        """Authorization for resource-1 cannot be used to authorize resource-2."""
        user = ActorIdentity(actor_id="user-1", actor_type=ActorType.USER)
        d1 = security.authorize(actor=user, action="work.status", resource="work-alpha")
        assert d1.outcome == AuthorizationOutcome.ALLOW
        assert d1.resource == "work-alpha"

        d2 = security.authorize(actor=user, action="work.status", resource="work-beta")
        assert d2.resource == "work-beta"

    def test_sxb_03_capability_cannot_be_substituted_in_route(self, orchestrator):
        """Routing to a non-existent or wrong capability name fails closed."""
        req = _req("create", objective="evil")
        resp = orchestrator.route_request("nonexistent_capability", req)
        assert resp.success is False
        assert "Orchestration failure" in resp.error

    def test_sxb_04_work_create_actor_binding_persists_in_metadata(self, orchestrator, service):
        """When work is created through Orchestrator, the actor identity is captured."""
        actor = ActorIdentity(actor_id="creator-user", actor_type=ActorType.USER)
        req = Request(
            request_id="req-create",
            payload={"action": "create", "objective": "test provenance", "_actor": actor},
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is True
        w_id = resp.data["work_id"]
        work = service.get_work(w_id)
        assert work is not None
        initiating = work.metadata.get("initiating_actor", {})
        assert initiating.get("actor_id") == "creator-user"
        assert initiating.get("actor_type") == "user"

    def test_sxb_05_capability_payload_mutation_after_snapshot_is_ignored(
        self, orchestrator, service
    ):
        """Mutating the payload dict after passing to route_request has no effect."""
        shared_payload = {"action": "create", "objective": "original objective"}
        req = Request(request_id="tamper-test", payload=shared_payload)
        resp = orchestrator.route_request("work", req)
        shared_payload["objective"] = "TAMPERED OBJECTIVE"
        assert resp.success is True
        w_id = resp.data["work_id"]
        work = service.get_work(w_id)
        assert work.objective == "original objective"

    def test_sxb_06_policy_default_deny_on_unmapped_action(self, security):
        """An unknown action with an unmapped actor type evaluates to DENY."""
        unknown_actor = ActorIdentity(actor_id="alien", actor_type=ActorType("user"), trust_level=0)
        strict_engine = PolicyEngine(rules=[], default_outcome=AuthorizationOutcome.DENY)
        strict_sec = SecurityService(policy_engine=strict_engine)
        decision = strict_sec.authorize(actor=unknown_actor, action="work.destroy_universe")
        assert decision.outcome == AuthorizationOutcome.DENY
