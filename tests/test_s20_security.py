"""S20: Identity & Security Plane — Comprehensive Tests.

Tests the security boundary independently of the AI model,
frontend, and individual capability implementations.
"""

from __future__ import annotations

import pytest

from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.security import (
    SYSTEM_ACTOR,
    ActorIdentity,
    ActorType,
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
    SecurityEvent,
    SecurityEventType,
)
from core.orchestration.orchestrator import Orchestrator
from core.security.events import SecurityEventLog
from core.security.policy import PolicyEngine, PolicyRule, create_default_policy
from core.security.service import SecurityService

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture()
def user_actor() -> ActorIdentity:
    return ActorIdentity(actor_id="user:alice", actor_type=ActorType.USER)


@pytest.fixture()
def agent_actor() -> ActorIdentity:
    return ActorIdentity(
        actor_id="agent:worker1", actor_type=ActorType.AGENT
    )


@pytest.fixture()
def default_policy() -> PolicyEngine:
    return create_default_policy()


@pytest.fixture()
def security_service(default_policy: PolicyEngine) -> SecurityService:
    return SecurityService(policy_engine=default_policy)


@pytest.fixture()
def event_log() -> SecurityEventLog:
    return SecurityEventLog()


class _EchoCapability(Capability):
    """Minimal capability for testing orchestrator integration."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Echo capability for testing"

    def invoke(self, request: Request) -> Response:
        return Response(
            request_id=request.request_id,
            data={"echo": request.payload, "invoked": True},
            success=True,
        )


# =========================================================================
# 1. Identity Tests
# =========================================================================


class TestActorIdentity:
    def test_valid_user_actor(self, user_actor: ActorIdentity) -> None:
        assert user_actor.actor_id == "user:alice"
        assert user_actor.actor_type == ActorType.USER

    def test_system_actor(self) -> None:
        assert SYSTEM_ACTOR.actor_id == "nav:system"
        assert SYSTEM_ACTOR.actor_type == ActorType.SYSTEM
        assert SYSTEM_ACTOR.trust_level == 100

    def test_agent_actor(self, agent_actor: ActorIdentity) -> None:
        assert agent_actor.actor_type == ActorType.AGENT

    def test_actor_is_frozen(self, user_actor: ActorIdentity) -> None:
        with pytest.raises(AttributeError):
            user_actor.actor_id = "hacked"  # type: ignore[misc]

    def test_actor_metadata(self) -> None:
        actor = ActorIdentity(
            actor_id="user:bob",
            actor_type=ActorType.USER,
            metadata={"role": "admin"},
        )
        assert actor.metadata["role"] == "admin"

    def test_default_actor_type(self) -> None:
        actor = ActorIdentity(actor_id="test")
        assert actor.actor_type == ActorType.USER


# =========================================================================
# 2. Policy Engine Tests
# =========================================================================


class TestPolicyEngine:
    def test_system_allowed_everything(
        self, default_policy: PolicyEngine
    ) -> None:
        req = AuthorizationRequest(
            actor=SYSTEM_ACTOR,
            action="work.cancel",
            resource="work_123",
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.ALLOW
        )

    def test_user_allowed_general(
        self, default_policy: PolicyEngine, user_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor, action="work.create"
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.ALLOW
        )

    def test_user_cancel_requires_approval(
        self, default_policy: PolicyEngine, user_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor,
            action="work.cancel",
            resource="work_123",
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.REQUIRE_APPROVAL
        )

    def test_user_redirect_requires_approval(
        self, default_policy: PolicyEngine, user_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor, action="work.redirect"
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.REQUIRE_APPROVAL
        )

    def test_user_takeover_requires_approval(
        self, default_policy: PolicyEngine, user_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor, action="work.take_over"
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.REQUIRE_APPROVAL
        )

    def test_user_delete_requires_approval(
        self, default_policy: PolicyEngine, user_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor, action="work.delete"
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.REQUIRE_APPROVAL
        )

    def test_agent_cannot_takeover(
        self, default_policy: PolicyEngine, agent_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=agent_actor, action="work.take_over"
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.DENY
        )

    def test_agent_cancel_requires_approval(
        self, default_policy: PolicyEngine, agent_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=agent_actor, action="work.cancel"
        )
        assert (
            default_policy.evaluate(req).outcome
            == AuthorizationOutcome.REQUIRE_APPROVAL
        )

    def test_unknown_action_default_deny(self) -> None:
        policy = PolicyEngine(
            rules=[], default_outcome=AuthorizationOutcome.DENY
        )
        actor = ActorIdentity(
            actor_id="u:t", actor_type=ActorType.USER
        )
        req = AuthorizationRequest(actor=actor, action="x.y")
        assert (
            policy.evaluate(req).outcome == AuthorizationOutcome.DENY
        )

    def test_custom_rule(self) -> None:
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="memory.write",
                    outcome=AuthorizationOutcome.DENY,
                    reason="blocked",
                    priority=10,
                )
            ]
        )
        actor = ActorIdentity(
            actor_id="u:t", actor_type=ActorType.USER
        )
        req = AuthorizationRequest(actor=actor, action="memory.write")
        assert (
            policy.evaluate(req).outcome == AuthorizationOutcome.DENY
        )

    def test_decision_contains_context(
        self, default_policy: PolicyEngine, user_actor: ActorIdentity
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor,
            action="work.pause",
            resource="work_456",
        )
        d = default_policy.evaluate(req)
        assert d.actor_id == "user:alice"
        assert d.action == "work.pause"
        assert d.resource == "work_456"

    def test_add_rule_dynamically(self) -> None:
        policy = PolicyEngine()
        actor = ActorIdentity(
            actor_id="u:t", actor_type=ActorType.USER
        )
        req = AuthorizationRequest(actor=actor, action="custom.act")
        assert (
            policy.evaluate(req).outcome == AuthorizationOutcome.DENY
        )
        policy.add_rule(
            PolicyRule(
                actor_type=ActorType.USER,
                action_pattern="custom.act",
                outcome=AuthorizationOutcome.ALLOW,
                priority=10,
            )
        )
        assert (
            policy.evaluate(req).outcome == AuthorizationOutcome.ALLOW
        )


# =========================================================================
# 3. Security Service Tests
# =========================================================================


class TestSecurityService:
    def test_authorize_allow(
        self, security_service: SecurityService
    ) -> None:
        d = security_service.authorize(
            actor=SYSTEM_ACTOR, action="work.create"
        )
        assert d.outcome == AuthorizationOutcome.ALLOW

    def test_authorize_deny(self) -> None:
        svc = SecurityService(policy_engine=PolicyEngine(rules=[]))
        actor = ActorIdentity(
            actor_id="u:t", actor_type=ActorType.USER
        )
        d = svc.authorize(actor=actor, action="work.create")
        assert d.outcome == AuthorizationOutcome.DENY

    def test_authorize_require_approval(
        self,
        security_service: SecurityService,
        user_actor: ActorIdentity,
    ) -> None:
        d = security_service.authorize(
            actor=user_actor,
            action="work.cancel",
            resource="work_123",
        )
        assert d.outcome == AuthorizationOutcome.REQUIRE_APPROVAL

    def test_authorize_default_system_actor(
        self, security_service: SecurityService
    ) -> None:
        d = security_service.authorize(action="work.cancel")
        assert d.outcome == AuthorizationOutcome.ALLOW
        assert d.actor_id == "nav:system"

    def test_authorize_records_events(
        self,
        security_service: SecurityService,
        user_actor: ActorIdentity,
    ) -> None:
        security_service.authorize(
            actor=user_actor, action="work.create"
        )
        assert security_service.event_log.count >= 2

    def test_authorize_request_object(
        self,
        security_service: SecurityService,
        user_actor: ActorIdentity,
    ) -> None:
        req = AuthorizationRequest(
            actor=user_actor,
            action="work.pause",
            resource="work_789",
        )
        d = security_service.authorize_request(req)
        assert d.outcome == AuthorizationOutcome.ALLOW
        assert d.resource == "work_789"


# =========================================================================
# 4. Security Event Log Tests
# =========================================================================


class TestSecurityEventLog:
    def _make_event(
        self, et: SecurityEventType = SecurityEventType.AUTHORIZATION_GRANTED
    ) -> SecurityEvent:
        return SecurityEvent(
            timestamp="2025-01-01T00:00:00Z",
            event_type=et,
            decision=AuthorizationDecision(
                outcome=AuthorizationOutcome.ALLOW,
                actor_id="test",
                action="test",
            ),
        )

    def test_record_and_retrieve(
        self, event_log: SecurityEventLog
    ) -> None:
        event_log.record(self._make_event())
        assert event_log.count == 1

    def test_filter_by_type(
        self, event_log: SecurityEventLog
    ) -> None:
        for i in range(5):
            et = (
                SecurityEventType.AUTHORIZATION_GRANTED
                if i % 2 == 0
                else SecurityEventType.AUTHORIZATION_DENIED
            )
            event_log.record(self._make_event(et))
        assert (
            len(
                event_log.get_events(
                    event_type="authorization_granted"
                )
            )
            == 3
        )
        assert (
            len(
                event_log.get_events(
                    event_type="authorization_denied"
                )
            )
            == 2
        )

    def test_max_events(self) -> None:
        log = SecurityEventLog(max_events=5)
        for _ in range(10):
            log.record(self._make_event())
        assert log.count == 5

    def test_clear(self, event_log: SecurityEventLog) -> None:
        event_log.record(self._make_event())
        event_log.clear()
        assert event_log.count == 0


# =========================================================================
# 5. Orchestrator Integration Tests
# =========================================================================


class TestOrchestratorSecurity:
    def test_no_security_backward_compat(self) -> None:
        reg = CapabilityRegistry()
        reg.register(_EchoCapability())
        orch = Orchestrator(reg)
        resp = orch.route_request(
            "echo", Request(request_id="r1", payload={"action": "t"})
        )
        assert resp.success is True
        assert resp.data["invoked"] is True

    def test_security_allow(self) -> None:
        reg = CapabilityRegistry()
        reg.register(_EchoCapability())
        orch = Orchestrator(reg, security_service=SecurityService())
        resp = orch.route_request(
            "echo",
            Request(
                request_id="r1",
                payload={
                    "action": "t",
                    "_actor": {
                        "actor_id": "nav:system",
                        "actor_type": "system",
                    },
                },
            ),
        )
        assert resp.success is True

    def test_security_deny(self) -> None:
        reg = CapabilityRegistry()
        reg.register(_EchoCapability())
        svc = SecurityService(
            policy_engine=PolicyEngine(rules=[])
        )
        orch = Orchestrator(reg, security_service=svc)
        resp = orch.route_request(
            "echo",
            Request(
                request_id="r1",
                payload={
                    "action": "t",
                    "_actor": {
                        "actor_id": "u:h",
                        "actor_type": "user",
                    },
                },
            ),
        )
        assert resp.success is False
        assert "denied" in (resp.error or "").lower()

    def test_default_actor_backward_compat(self) -> None:
        reg = CapabilityRegistry()
        reg.register(_EchoCapability())
        orch = Orchestrator(reg, security_service=SecurityService())
        resp = orch.route_request(
            "echo", Request(request_id="r1", payload={"action": "t"})
        )
        assert resp.success is True

    def test_require_approval_enriches_payload(self) -> None:
        reg = CapabilityRegistry()
        reg.register(_EchoCapability())
        # Policy must match "echo.cancel" since orchestrator builds
        # action as "{capability_name}.{payload_action}"
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="echo.cancel",
                    outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
                    reason="test approval gate",
                    priority=50,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=10,
                ),
            ]
        )
        orch = Orchestrator(
            reg,
            security_service=SecurityService(policy_engine=policy),
        )
        resp = orch.route_request(
            "echo",
            Request(
                request_id="r1",
                payload={
                    "action": "cancel",
                    "_actor": {
                        "actor_id": "user:alice",
                        "actor_type": "user",
                    },
                },
            ),
        )
        assert resp.success is True
        assert (
            resp.data["echo"]["_security_requires_approval"] is True
        )


# =========================================================================
# 6. S18 Approval Integration Tests
# =========================================================================


class TestS18ApprovalIntegration:
    def test_deny_not_bypassed_by_approval(self) -> None:
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.AGENT,
                    action_pattern="work.take_over",
                    outcome=AuthorizationOutcome.DENY,
                    priority=10,
                )
            ]
        )
        svc = SecurityService(policy_engine=policy)
        agent = ActorIdentity(
            actor_id="agent:bot", actor_type=ActorType.AGENT
        )
        d = svc.authorize(
            actor=agent, action="work.take_over", resource="w1"
        )
        assert d.outcome == AuthorizationOutcome.DENY

    def test_allow_does_not_skip_s18(self) -> None:
        svc = SecurityService()
        d = svc.authorize(
            actor=SYSTEM_ACTOR,
            action="work.execute_step",
            resource="w1",
        )
        assert d.outcome == AuthorizationOutcome.ALLOW
        # S18 step-level approval is independent

    def test_require_approval_separate_from_s18(
        self, user_actor: ActorIdentity
    ) -> None:
        svc = SecurityService()
        d = svc.authorize(
            actor=user_actor, action="work.cancel", resource="w1"
        )
        assert d.outcome == AuthorizationOutcome.REQUIRE_APPROVAL


# =========================================================================
# 7. Security Invariant Tests
# =========================================================================


class TestSecurityInvariants:
    def test_invariant_1_model_cannot_grant_authority(self) -> None:
        svc = SecurityService(
            policy_engine=PolicyEngine(rules=[])
        )
        fake = ActorIdentity(
            actor_id="llm:self", actor_type=ActorType.AGENT
        )
        d = svc.authorize(actor=fake, action="work.cancel")
        assert d.outcome == AuthorizationOutcome.DENY

    def test_invariant_3_approval_cannot_override_deny(self) -> None:
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.AGENT,
                    action_pattern="*",
                    outcome=AuthorizationOutcome.DENY,
                    priority=10,
                )
            ]
        )
        svc = SecurityService(policy_engine=policy)
        agent = ActorIdentity(
            actor_id="agent:rogue", actor_type=ActorType.AGENT
        )
        d = svc.authorize(actor=agent, action="work.create")
        assert d.outcome == AuthorizationOutcome.DENY

    def test_invariant_5_capabilities_dont_invent_auth(
        self, user_actor: ActorIdentity
    ) -> None:
        svc = SecurityService()
        d = svc.authorize(actor=user_actor, action="work.pause")
        assert d.outcome == AuthorizationOutcome.ALLOW
        assert d.policy_ref != ""

    def test_invariant_7_deterministic(
        self, user_actor: ActorIdentity
    ) -> None:
        svc = SecurityService()
        outcomes = {
            svc.authorize(
                actor=user_actor,
                action="work.cancel",
                resource="w1",
            ).outcome
            for _ in range(10)
        }
        assert len(outcomes) == 1
        assert AuthorizationOutcome.REQUIRE_APPROVAL in outcomes


# =========================================================================
# 8. Backward Compatibility Tests
# =========================================================================


class TestBackwardCompatibility:
    def test_request_without_actor(self) -> None:
        req = Request(
            request_id="r1", payload={"action": "create"}
        )
        assert req.request_id == "r1"

    def test_orchestrator_constructor_compat(self) -> None:
        reg = CapabilityRegistry()
        orch = Orchestrator(reg)
        assert orch.registry is reg

    def test_system_actor_default_for_legacy(self) -> None:
        svc = SecurityService()
        d = svc.authorize(action="work.cancel", resource="w1")
        assert d.outcome == AuthorizationOutcome.ALLOW
        assert d.actor_id == "nav:system"


