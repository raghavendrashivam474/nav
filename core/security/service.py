"""Security service — S20.

Central authorization service that evaluates requests against policy
and records security events for observability.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.contracts.security import (
    SYSTEM_ACTOR,
    ActorIdentity,
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
    SecurityEvent,
    SecurityEventType,
)
from core.log import get_logger
from core.security.events import SecurityEventLog
from core.security.policy import PolicyEngine, create_default_policy

logger = get_logger(__name__)


class SecurityService:
    """Central authorization service for NAV.

    Evaluates whether an actor is permitted to perform an action
    against a resource, independently of the AI model and frontend.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine | None = None,
        event_log: SecurityEventLog | None = None,
    ) -> None:
        self._policy = policy_engine or create_default_policy()
        self._events = event_log or SecurityEventLog()

    @property
    def policy_engine(self) -> PolicyEngine:
        return self._policy

    @property
    def event_log(self) -> SecurityEventLog:
        return self._events

    def authorize(
        self,
        actor: ActorIdentity | None = None,
        action: str = "",
        resource: str = "",
        context: dict[str, Any] | None = None,
    ) -> AuthorizationDecision:
        """Evaluate whether the given actor may perform the action.

        If no actor is provided, defaults to the system actor for
        backward compatibility with S17-S19 code paths.
        """
        effective_actor = actor or SYSTEM_ACTOR
        request = AuthorizationRequest(
            actor=effective_actor,
            action=action,
            resource=resource,
            context=context or {},
        )

        self._record_event(
            SecurityEventType.AUTHORIZATION_REQUESTED, request
        )

        decision = self._policy.evaluate(request)

        event_type = {
            AuthorizationOutcome.ALLOW: SecurityEventType.AUTHORIZATION_GRANTED,
            AuthorizationOutcome.DENY: SecurityEventType.AUTHORIZATION_DENIED,
            AuthorizationOutcome.REQUIRE_APPROVAL: (
                SecurityEventType.APPROVAL_REQUIRED
            ),
        }[decision.outcome]

        self._record_event(event_type, request, decision)

        logger.info(
            "Security: %s actor=%s action=%s resource=%s reason=%s",
            decision.outcome.value,
            effective_actor.actor_id,
            action,
            resource,
            decision.reason,
        )

        return decision

    def authorize_request(
        self, request: AuthorizationRequest
    ) -> AuthorizationDecision:
        """Evaluate a pre-constructed authorization request."""
        return self.authorize(
            actor=request.actor,
            action=request.action,
            resource=request.resource,
            context=request.context,
        )

    def _record_event(
        self,
        event_type: SecurityEventType,
        request: AuthorizationRequest,
        decision: AuthorizationDecision | None = None,
    ) -> None:
        if decision is None:
            decision = AuthorizationDecision(
                outcome=AuthorizationOutcome.ALLOW,
                actor_id=request.actor.actor_id,
                action=request.action,
                resource=request.resource,
                reason="pending",
            )
        event = SecurityEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            decision=decision,
        )
        self._events.record(event)
