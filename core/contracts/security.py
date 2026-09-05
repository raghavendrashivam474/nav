"""Security contracts — S20: Identity & Security Plane.

Defines the core abstractions for identity, authorization, and security
enforcement. These contracts are independent of the AI model, frontend,
and individual capability implementations.

Key principles:
- Identity is separate from authentication mechanism.
- Authorization is deterministic and policy-driven.
- Security decisions are observable and inspectable.
- Human approval and security authorization are separate gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class ActorType(str, Enum):
    """Classification of the entity making a request."""

    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"


@dataclass(frozen=True)
class ActorIdentity:
    """Stable representation of who is making a request.

    This is the minimal identity abstraction NAV needs.
    It is NOT a full IAM model — it is a foundation to evolve.
    """

    actor_id: str
    actor_type: ActorType = ActorType.USER
    trust_level: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# Well-known system actor for backward compatibility.
# Used when no explicit actor is provided (S17-S19 legacy paths).
SYSTEM_ACTOR = ActorIdentity(
    actor_id="nav:system",
    actor_type=ActorType.SYSTEM,
    trust_level=100,
)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


class AuthorizationOutcome(str, Enum):
    """Result of an authorization evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(frozen=True)
class AuthorizationRequest:
    """A request to evaluate whether an actor may perform an action."""

    actor: ActorIdentity
    action: str
    resource: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthorizationDecision:
    """Structured, deterministic result of an authorization evaluation."""

    outcome: AuthorizationOutcome
    actor_id: str
    action: str
    resource: str = ""
    reason: str = ""
    policy_ref: str = ""


# ---------------------------------------------------------------------------
# Security Observability
# ---------------------------------------------------------------------------


class SecurityEventType(str, Enum):
    """Types of security events for operational traceability."""

    AUTHORIZATION_REQUESTED = "authorization_requested"
    AUTHORIZATION_GRANTED = "authorization_granted"
    AUTHORIZATION_DENIED = "authorization_denied"
    APPROVAL_REQUIRED = "approval_required"


@dataclass(frozen=True)
class SecurityEvent:
    """A recorded security decision for observability."""

    timestamp: str
    event_type: SecurityEventType
    decision: AuthorizationDecision
