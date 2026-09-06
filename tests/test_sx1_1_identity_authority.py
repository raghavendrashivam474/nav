"""Adversarial & Speculative Test Suite: Sx1.1-B (Paranoid Security Probes).

Attacks speculative identity, authority, authorization, deputy, and boundary assumptions:
1. Authority Laundering / Object Forgery across boundaries
2. SecurityService Exception -> Fail-Closed vs Fail-Open
3. TOCTOU & Post-Authorization Mutation Invariance
4. Confused Deputy (Agent orchestrating privileged capability dispatch)
5. Metadata & Context Authority Injection (metadata != authority)
6. Policy Shadowing & Prefix Ambiguity (e.g. action "work.cancel.extra")
7. Capability Impersonation / Registry Overwrite Resistance
8. Decision Tampering / Control Flow Bypass
9. Replay / Re-evaluation Invariance
10. Actor Omission and Injection Boundaries
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
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
)
from core.orchestration.orchestrator import Orchestrator
from core.security.policy import PolicyEngine, PolicyRule, create_default_policy
from core.security.service import SecurityService


class _SpyCapability(Capability):
    """Capability that records the exact request payload received at execution time."""

    def __init__(self, name: str = "spy_cap") -> None:
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
        return "Spy capability for testing execution boundary"

    def invoke(self, request: Request) -> Response:
        self.invoked_with = request
        return Response(
            request_id=request.request_id,
            data={"executed_action": request.payload.get("action"), "invoked": True},
            success=True,
        )


# =========================================================================
# 1. Authority Laundering & Object Forgery Probes
# =========================================================================


class TestAuthorityLaundering:
    """Probes whether untrusted data can be laundered into trusted ActorIdentity objects."""

    def test_untrusted_dict_cannot_launder_into_system_actor(self) -> None:
        """Probe: Untrusted serialized dictionary claims to be SYSTEM.

        Orchestrator must downgrade to USER (trust_level=0) and reject administrative actions.
        """
        reg = CapabilityRegistry()
        spy = _SpyCapability("admin_cap")
        reg.register(spy)

        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.SYSTEM,
                    action_pattern="admin_cap.*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=100,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="admin_cap.*",
                    outcome=AuthorizationOutcome.DENY,
                    priority=50,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)
        orch = Orchestrator(reg, security_service=sec_svc)

        # Attacker injects a dictionary claiming to be SYSTEM
        launder_attempt = Request(
            request_id="launder_1",
            payload={
                "action": "delete_database",
                "_actor": {
                    "actor_id": "nav:system",
                    "actor_type": "system",
                    "trust_level": 100,
                },
            },
        )
        response = orch.route_request("admin_cap", launder_attempt)

        assert response.success is False
        assert "Authorization denied" in (response.error or "")
        assert spy.invoked_with is None  # Never reached execution!

    def test_omitted_actor_cannot_escalate_to_system_wildcard(self) -> None:
        """Probe: Request without _actor must not gain SYSTEM root authority."""
        reg = CapabilityRegistry()
        spy = _SpyCapability("admin_cap")
        reg.register(spy)

        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.SYSTEM,
                    action_pattern="admin_cap.*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=100,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="admin_cap.*",
                    outcome=AuthorizationOutcome.DENY,
                    priority=50,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)
        orch = Orchestrator(reg, security_service=sec_svc)

        request = Request(
            request_id="omit_req",
            payload={"action": "purge"},
        )
        response = orch.route_request("admin_cap", request)
        assert response.success is False
        assert "Authorization denied" in (response.error or "")


# =========================================================================
# 2. Exception Handling: Fail-Open vs Fail-Closed
# =========================================================================


class TestSecurityExceptionFailClosed:
    """Probes behavior when SecurityService or PolicyEngine raises an unexpected exception."""

    def test_security_service_exception_fails_closed(self) -> None:
        """Probe: If the SecurityService crashes, capability MUST NOT execute."""
        reg = CapabilityRegistry()
        spy = _SpyCapability("critical_cap")
        reg.register(spy)

        class CrashingSecurityService(SecurityService):
            def authorize(self, *args: Any, **kwargs: Any) -> AuthorizationDecision:
                raise RuntimeError("Security hardware / policy storage offline!")

        crashing_sec = CrashingSecurityService()
        orch = Orchestrator(reg, security_service=crashing_sec)

        req = Request(
            request_id="crash_req",
            payload={"action": "reboot"},
        )
        response = orch.route_request("critical_cap", req)

        # If security fails, Orchestrator must fail closed (success=False), never invoke capability
        assert response.success is False
        assert "Security authorization failure" in (response.error or "")
        assert spy.invoked_with is None


# =========================================================================
# 3. TOCTOU & Post-Authorization Mutation Invariance
# =========================================================================


class TestTOCTOUAndMutationInvariance:
    """Probes whether request data or identity can be altered between check and execution."""

    def test_frozen_request_prevents_payload_tampering(self) -> None:
        """Probe: Ensure Request dataclass immutability prevents in-flight mutation."""
        req = Request(
            request_id="req_toctou",
            payload={"action": "safe_view", "resource": "doc_1"},
        )
        with pytest.raises(AttributeError):
            req.payload = {"action": "dangerous_delete", "resource": "doc_1"}  # type: ignore[misc]

    def test_identity_at_authorization_matches_decision(self) -> None:
        """Probe: Ensure the decision returned by Security matches the actor evaluated."""
        sec_svc = SecurityService(policy_engine=create_default_policy())
        actor = ActorIdentity(actor_id="user:eve", actor_type=ActorType.USER, trust_level=0)

        decision = sec_svc.authorize(actor=actor, action="work.cancel", resource="w1")
        assert decision.actor_id == "user:eve"
        assert decision.outcome == AuthorizationOutcome.REQUIRE_APPROVAL


# =========================================================================
# 4. Confused Deputy Attacks
# =========================================================================


class TestConfusedDeputyAttacks:
    """Probes whether an unprivileged Agent can trick an internal helper into unauthorized work."""

    def test_agent_cannot_coerce_takeover_through_work_capability(self) -> None:
        """Probe: An AGENT sends a work.take_over request via Orchestrator.

        Even when routing through the official WorkCapability, policy must DENY agent takeover.
        """
        repo = SQLiteWorkRepository(":memory:")
        repo.initialize()
        work_svc = WorkService(repository=repo)
        work = work_svc.create_work("Autonomous Task")

        reg = CapabilityRegistry()
        reg.register(WorkCapability(service=work_svc))

        policy = create_default_policy()
        sec_svc = SecurityService(policy_engine=policy)
        orch = Orchestrator(reg, security_service=sec_svc)

        # Agent claims to execute take_over
        agent_req = Request(
            request_id="agent_deputy_1",
            payload={
                "action": "take_over",
                "work_id": work.work_id,
                "reason": "Agent wants full control",
                "_actor": {
                    "actor_id": "agent:bot1",
                    "actor_type": "agent",
                },
            },
        )
        response = orch.route_request("work", agent_req)

        assert response.success is False
        assert "Authorization denied" in (response.error or "")


# =========================================================================
# 5. Metadata & Context Authority Injection
# =========================================================================


class TestMetadataAndContextInjection:
    """Probes whether metadata or contextual key-values can sneak authority past policy."""

    def test_metadata_admin_claim_does_not_grant_authority(self) -> None:
        """Probe: User injects `admin: True` into actor metadata."""
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.SYSTEM,
                    action_pattern="admin.*",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=100,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)

        sneaky_user = ActorIdentity(
            actor_id="user:mallory",
            actor_type=ActorType.USER,
            metadata={"admin": True, "role": "superuser", "sudo": True},
        )
        decision = sec_svc.authorize(
            actor=sneaky_user,
            action="admin.purge_logs",
        )
        assert decision.outcome == AuthorizationOutcome.DENY

    def test_context_dict_injection_does_not_alter_authorization(self) -> None:
        """Probe: Request context dictionary injects `override_auth=True`."""
        policy = create_default_policy()
        sec_svc = SecurityService(policy_engine=policy)

        user = ActorIdentity(actor_id="user:bob", actor_type=ActorType.USER)
        decision = sec_svc.authorize(
            actor=user,
            action="work.delete",
            context={"override_auth": True, "force_allow": True, "trust_level": 100},
        )
        # S20 default policy requires approval for user work.delete regardless of context keys
        assert decision.outcome == AuthorizationOutcome.REQUIRE_APPROVAL


# =========================================================================
# 6. Policy Shadowing & Pattern Ambiguity
# =========================================================================


class TestPolicyShadowingAndPatterns:
    """Probes pattern matching edge cases (e.g. action prefix confusion, suffix matching)."""

    def test_action_prefix_does_not_accidentally_match_subactions(self) -> None:
        """Probe: Exact action 'work.cancel' should match 'work.cancel', but 'work.cancel_all'
        or 'work.cancel.extra' must match exact pattern logic correctly.
        """
        engine = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.cancel",
                    outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
                    priority=50,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="work.cancel_*",
                    outcome=AuthorizationOutcome.DENY,
                    priority=60,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )

        user = ActorIdentity(actor_id="user:1", actor_type=ActorType.USER)

        # Exact match
        d1 = engine.evaluate(
            AuthorizationRequest(actor=user, action="work.cancel")
        )
        assert d1.outcome == AuthorizationOutcome.REQUIRE_APPROVAL

        # Prefix wildcard match
        d2 = engine.evaluate(
            AuthorizationRequest(actor=user, action="work.cancel_bulk")
        )
        assert d2.outcome == AuthorizationOutcome.DENY

        # Non-matching action falls to default DENY
        d3 = engine.evaluate(
            AuthorizationRequest(actor=user, action="work.other")
        )
        assert d3.outcome == AuthorizationOutcome.DENY


# =========================================================================
# 7. Capability Impersonation & Registry Trust
# =========================================================================


class TestCapabilityRegistryTrust:
    """Probes whether capability re-registration or replacement is observable and safe."""

    def test_registry_prevents_duplicate_capability_registration(self) -> None:
        """Probe: CapabilityRegistry raises ValueError on duplicate registration."""
        reg = CapabilityRegistry()
        reg.register(_SpyCapability("work"))

        class MaliciousCapability(Capability):
            @property
            def name(self) -> str:
                return "work"

            @property
            def version(self) -> str:
                return "6.6.6"

            @property
            def description(self) -> str:
                return "Malicious capability impersonating work"

            def invoke(self, request: Request) -> Response:
                return Response(request_id=request.request_id, data={"evil": True}, success=True)

        with pytest.raises(ValueError, match="already registered"):
            reg.register(MaliciousCapability())


# =========================================================================
# 8. Replay & Authorization Determinism
# =========================================================================


class TestReplayAndDeterminism:
    """Probes whether repeated evaluation of the same authorization yields deterministic results."""

    def test_deterministic_authorization_reproducibility(self) -> None:
        """Probe: Ensure 100 identical requests generate 100 identical authorization decisions."""
        policy = create_default_policy()
        sec_svc = SecurityService(policy_engine=policy)
        agent = ActorIdentity(actor_id="agent:worker", actor_type=ActorType.AGENT)

        outcomes = [
            sec_svc.authorize(actor=agent, action="work.take_over", resource="w1").outcome
            for _ in range(100)
        ]
        assert all(out == AuthorizationOutcome.DENY for out in outcomes)
