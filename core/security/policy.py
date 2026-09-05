"""Deterministic policy engine — S20.

Evaluates authorization requests against a set of explicit rules.
No LLM involvement. No prompt-based security. Pure deterministic logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.contracts.security import (
    ActorType,
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
)


@dataclass(frozen=True)
class PolicyRule:
    """A single authorization rule.

    Rules are evaluated in priority order. The first matching rule wins.
    """

    actor_type: ActorType | None = None
    action_pattern: str = ""
    resource_pattern: str = ""
    outcome: AuthorizationOutcome = AuthorizationOutcome.ALLOW
    reason: str = ""
    priority: int = 0


class PolicyEngine:
    """Deterministic policy evaluation engine.

    Evaluates authorization requests against an ordered set of rules.
    If no rule matches, the default outcome is DENY (fail-closed).
    """

    def __init__(
        self,
        rules: list[PolicyRule] | None = None,
        default_outcome: AuthorizationOutcome = AuthorizationOutcome.DENY,
    ) -> None:
        self._rules: list[PolicyRule] = sorted(
            rules or [], key=lambda r: r.priority, reverse=True
        )
        self._default_outcome = default_outcome

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, request: AuthorizationRequest) -> AuthorizationDecision:
        for rule in self._rules:
            if self._matches(rule, request):
                return AuthorizationDecision(
                    outcome=rule.outcome,
                    actor_id=request.actor.actor_id,
                    action=request.action,
                    resource=request.resource,
                    reason=rule.reason or "Matched policy rule",
                    policy_ref=f"rule:{rule.action_pattern}:{rule.actor_type}",
                )

        return AuthorizationDecision(
            outcome=self._default_outcome,
            actor_id=request.actor.actor_id,
            action=request.action,
            resource=request.resource,
            reason="No matching policy rule; default deny",
            policy_ref="default",
        )

    @staticmethod
    def _matches(rule: PolicyRule, request: AuthorizationRequest) -> bool:
        if (
            rule.actor_type is not None
            and rule.actor_type != request.actor.actor_type
        ):
            return False
        if rule.action_pattern and not _pattern_matches(
            rule.action_pattern, request.action
        ):
            return False
        if rule.resource_pattern and not _pattern_matches(
            rule.resource_pattern, request.resource
        ):
            return False
        return True


def _pattern_matches(pattern: str, value: str) -> bool:
    """Simple prefix/exact matching for policy patterns.

    Supports:
    - Exact match: ``"work.cancel"`` matches ``"work.cancel"``
    - Prefix match: ``"work."`` matches ``"work.cancel"``, ``"work.pause"``
    - Wildcard: ``"*"`` matches everything
    """
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def create_default_policy() -> PolicyEngine:
    """Create the default NAV security policy.

    Default rules (priority order):
    1. System actor: ALLOW everything (backward compat for S17-S19).
    2. User/Agent: REQUIRE_APPROVAL for sensitive/destructive actions.
    3. Agent: DENY takeover.
    4. User/Agent: ALLOW general actions.
    5. Default: DENY (fail-closed for unknown actors).
    """
    rules = [
        # System actor: full access (backward compatibility)
        PolicyRule(
            actor_type=ActorType.SYSTEM,
            action_pattern="*",
            outcome=AuthorizationOutcome.ALLOW,
            reason="System actor: full access",
            priority=100,
        ),
        # User: sensitive actions require approval
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
            reason="Human takeover requires approval confirmation",
            priority=50,
        ),
        PolicyRule(
            actor_type=ActorType.USER,
            action_pattern="work.delete",
            outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
            reason="Work deletion requires human approval",
            priority=50,
        ),
        # User: general access
        PolicyRule(
            actor_type=ActorType.USER,
            action_pattern="*",
            outcome=AuthorizationOutcome.ALLOW,
            reason="User actor: general access granted",
            priority=10,
        ),
        # Agent: control actions
        PolicyRule(
            actor_type=ActorType.AGENT,
            action_pattern="work.cancel",
            outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
            reason="Agent cannot cancel work without approval",
            priority=50,
        ),
        PolicyRule(
            actor_type=ActorType.AGENT,
            action_pattern="work.redirect",
            outcome=AuthorizationOutcome.REQUIRE_APPROVAL,
            reason="Agent cannot redirect work without approval",
            priority=50,
        ),
        PolicyRule(
            actor_type=ActorType.AGENT,
            action_pattern="work.take_over",
            outcome=AuthorizationOutcome.DENY,
            reason="Agent cannot take over work",
            priority=50,
        ),
        # Agent: general execution access
        PolicyRule(
            actor_type=ActorType.AGENT,
            action_pattern="*",
            outcome=AuthorizationOutcome.ALLOW,
            reason="Agent actor: execution access granted",
            priority=10,
        ),
    ]
    return PolicyEngine(rules=rules, default_outcome=AuthorizationOutcome.DENY)
