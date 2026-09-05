# ADR-009: S20 Identity & Security Plane — Enforcement Architecture

## Status
Accepted

## Context
S17-S19 established work execution, human control, and interaction
boundaries. NAV lacked an independent authorization layer answering:
"Is this actor actually permitted to perform this action?" The model,
frontend, and capabilities could each independently allow actions
without a unified security gate.

## Decision

### Enforcement Point: Orchestrator
Authorization is enforced in `Orchestrator.route_request()` before
capability dispatch. This is the single dispatch point for all
capability invocations, ensuring every path encounters authorization
regardless of entry point (Interaction, Voice, CLI, direct).

### Backward Compatibility: SYSTEM_ACTOR Default
When no actor is provided in the request payload, the SecurityService
defaults to `SYSTEM_ACTOR` (ActorType.SYSTEM, trust_level=100). This
preserves all S17-S19 behavior without requiring changes to existing
callers.

### Policy Model: Ordered Rules, Fail-Closed
The PolicyEngine evaluates an ordered list of PolicyRules. First match
wins. Default outcome is DENY (fail-closed). Rules support actor_type,
action_pattern (exact/prefix/wildcard), and resource_pattern matching.

### S18 Approval Separation
Security authorization (ALLOW/DENY/REQUIRE_APPROVAL) is a separate
gate from S18 human approval (step-level `requires_approval`). A
security DENY cannot be bypassed by S18 approval. A security ALLOW
does not skip S18 approval when a step requires it.

### Actor Identity in Request Payload
Actor identity is passed via `_actor` key in the Request payload dict.
This avoids modifying the frozen `Request` dataclass and the
`Capability.invoke()` protocol.

## Options Considered

1. **Enforce at Capability level** — Rejected: would require modifying
   every capability, violates "capabilities don't invent auth" invariant.
2. **Enforce at Interaction layer** — Rejected: would leave direct
   Orchestrator/Service calls unprotected.
3. **Modify Request dataclass** — Rejected: frozen dataclass, would
   break all existing callers.
4. **Require actor on all calls** — Rejected: would break S17-S19
   backward compatibility.

## Consequences
- All capability invocations through the Orchestrator are now subject
  to authorization.
- Direct WorkService calls (bypassing Orchestrator) are NOT yet
  protected — known limitation for future sprints.
- The security plane is additive and does not alter existing S17-S19
  behavior.
- Future sprints can strengthen authentication, add persistent
  policies, and extend enforcement to direct service calls.
