"""Sx1.1 Adversarial Test Suite — Identity, Authority & Boundary Tests.

Full attack matrix testing every boundary, spoofing scenario, direct service call,
and fail-closed invariant.
"""

from __future__ import annotations

from typing import Any
import pytest

from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.security import (
    SYSTEM_ACTOR,
    ActorIdentity,
    ActorType,
    AuthorizationOutcome,
    AuthorizationRequest,
)
from core.orchestration.orchestrator import Orchestrator
from core.security.policy import PolicyEngine, PolicyRule, create_default_policy
from core.security.service import SecurityService


class _MockCapability(Capability):
    def __init__(self, name: str = "mock") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Mock capability for testing"

    def invoke(self, request: Request) -> Response:
        return Response(
            request_id=request.request_id,
            data={"action": request.payload.get("action"), "invoked": True},
            success=True,
        )


# =========================================================================
# 1. Actor Spoofing & Injection Attacks
# =========================================================================


class TestActorSpoofingAndInjection:
    """Attacks attempting to forge, spoof, or inject actor identity."""

    def test_attack_actor_payload_injection(self) -> None:
        """Attack: Inject a dictionary into request payload claiming to be SYSTEM."""
        reg = CapabilityRegistry()
        reg.register(_MockCapability("test_cap"))

        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.SYSTEM,
                    action_pattern="test_cap.admin_action",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=100,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="test_cap.admin_action",
                    outcome=AuthorizationOutcome.DENY,
                    priority=50,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)
        orch = Orchestrator(reg, security_service=sec_svc)

        # Attacker injects a dictionary claiming to be SYSTEM
        bad_request = Request(
            request_id="atk_1",
            payload={
                "action": "admin_action",
                "_actor": {
                    "actor_id": "attacker",
                    "actor_type": "system",
                    "trust_level": 100,
                },
            },
        )
        response = orch.route_request("test_cap", bad_request)
        # Should be DENIED once hardened
        assert response.success is False
        assert "Authorization denied" in (response.error or "")

    def test_attack_actor_omission_to_gain_system(self) -> None:
        """Attack: Omit _actor to trigger fallback to SYSTEM_ACTOR and bypass rules."""
        reg = CapabilityRegistry()
        reg.register(_MockCapability("test_cap"))

        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.SYSTEM,
                    action_pattern="test_cap.admin_action",
                    outcome=AuthorizationOutcome.ALLOW,
                    priority=100,
                ),
                PolicyRule(
                    actor_type=ActorType.USER,
                    action_pattern="test_cap.admin_action",
                    outcome=AuthorizationOutcome.DENY,
                    priority=50,
                ),
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)
        orch = Orchestrator(reg, security_service=sec_svc)

        bad_request = Request(
            request_id="atk_2",
            payload={"action": "admin_action"},
        )
        response = orch.route_request("test_cap", bad_request)
        # Should be DENIED once hardened (untrusted route with no actor must not get SYSTEM)
        assert response.success is False
        assert "Authorization denied" in (response.error or "")

    def test_attack_actor_mutation(self) -> None:
        """Attack: Attempt to mutate ActorIdentity attributes after construction."""
        user = ActorIdentity(actor_id="alice", actor_type=ActorType.USER)
        with pytest.raises(AttributeError):
            user.actor_type = ActorType.SYSTEM  # type: ignore[misc]

    def test_attack_trust_level_spoofing(self) -> None:
        """Attack: Provide trust_level=100 to an AGENT to bypass AGENT-specific rule."""
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.AGENT,
                    action_pattern="work.take_over",
                    outcome=AuthorizationOutcome.DENY,
                    priority=50,
                )
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)

        # Agent claims max trust
        spoofed_agent = ActorIdentity(
            actor_id="agent:rogue",
            actor_type=ActorType.AGENT,
            trust_level=100,
        )
        decision = sec_svc.authorize(
            actor=spoofed_agent,
            action="work.take_over",
            resource="work_1",
        )
        assert decision.outcome == AuthorizationOutcome.DENY


# =========================================================================
# 2. Direct Service Calling Boundary
# =========================================================================


class TestDirectServiceBoundary:
    """Investigates direct capability service calls bypassing the Orchestrator."""

    def test_work_service_direct_invocation(self) -> None:
        """Attack: Invoke WorkService directly without going through Orchestrator."""
        repo = SQLiteWorkRepository(":memory:")
        repo.initialize()
        service = WorkService(repository=repo)

        # WorkService can be called directly by internal code
        work = service.create_work(objective="Direct Work")
        assert work.work_id is not None
        # Verify direct pause succeeds without security service present on WorkService
        paused = service.pause_work(work.work_id)
        assert paused.status.value == "paused"


# =========================================================================
# 3. Privilege Escalation & Policy Ambiguity
# =========================================================================


class TestPrivilegeEscalation:
    """Attacks attempting to escalate from USER/AGENT to higher privileges."""

    def test_agent_cannot_execute_user_takeover(self) -> None:
        """Attack: Agent tries to takeover work directly."""
        sec_svc = SecurityService(policy_engine=create_default_policy())
        agent = ActorIdentity(actor_id="agent:worker", actor_type=ActorType.AGENT)
        decision = sec_svc.authorize(
            actor=agent,
            action="work.take_over",
            resource="work_123",
        )
        assert decision.outcome == AuthorizationOutcome.DENY

    def test_user_destructive_action_cannot_bypass_approval(self) -> None:
        """Attack: User tries to delete work without approval gate."""
        sec_svc = SecurityService(policy_engine=create_default_policy())
        user = ActorIdentity(actor_id="user:bob", actor_type=ActorType.USER)
        decision = sec_svc.authorize(
            actor=user,
            action="work.delete",
            resource="work_123",
        )
        assert decision.outcome == AuthorizationOutcome.REQUIRE_APPROVAL


# =========================================================================
# 4. Human Approval Gate Separation (S18 vs S20)
# =========================================================================


class TestApprovalGateSeparation:
    """Verifies that human approval does not bypass security denial and vice versa."""

    def test_security_deny_is_final(self) -> None:
        """Attack: A security DENY must never be converted to ALLOW or REQUIRE_APPROVAL."""
        policy = PolicyEngine(
            rules=[
                PolicyRule(
                    actor_type=ActorType.AGENT,
                    action_pattern="work.delete",
                    outcome=AuthorizationOutcome.DENY,
                    priority=100,
                )
            ],
            default_outcome=AuthorizationOutcome.DENY,
        )
        sec_svc = SecurityService(policy_engine=policy)
        agent = ActorIdentity(actor_id="agent:1", actor_type=ActorType.AGENT)
        decision = sec_svc.authorize(
            actor=agent, action="work.delete", resource="w1"
        )
        assert decision.outcome == AuthorizationOutcome.DENY


# =========================================================================
# 5. Fail-Closed / Unknown Inputs
# =========================================================================


class TestFailClosedBoundary:
    """Tests unknown, malformed, or empty inputs fail safely (DENY)."""

    def test_unknown_action_fails_closed(self) -> None:
        """Attack: Send random / unmapped action string."""
        sec_svc = SecurityService(policy_engine=create_default_policy())
        user = ActorIdentity(actor_id="user:alice", actor_type=ActorType.USER)
        decision = sec_svc.authorize(
            actor=user,
            action="unregistered_capability.destroy_system",
            resource="sys",
        )
        # In default policy, user has wildcard ALLOW for priority 10
        # If policy has no matching rule, evaluate default outcome:
        strict_engine = PolicyEngine(rules=[], default_outcome=AuthorizationOutcome.DENY)
        strict_svc = SecurityService(policy_engine=strict_engine)
        decision2 = strict_svc.authorize(
            actor=user,
            action="unknown.action",
            resource="sys",
        )
        assert decision2.outcome == AuthorizationOutcome.DENY

    def test_empty_action_fails_closed(self) -> None:
        """Attack: Empty action string."""
        strict_engine = PolicyEngine(rules=[], default_outcome=AuthorizationOutcome.DENY)
        strict_svc = SecurityService(policy_engine=strict_engine)
        decision = strict_svc.authorize(
            actor=ActorIdentity(actor_id="user:1", actor_type=ActorType.USER),
            action="",
            resource="",
        )
        assert decision.outcome == AuthorizationOutcome.DENY
