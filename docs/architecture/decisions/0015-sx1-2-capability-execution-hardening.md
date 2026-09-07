# ADR-0015: Sx1.2 Capability & Execution Boundary Hardening

## Status
Accepted

## Context
During the Sx1.2 adversarial campaign, three critical vulnerabilities and structural weaknesses were discovered at the capability and execution boundaries:

1. **REQUIRE_APPROVAL Execution Escape (VULN-01):** When `SecurityService.authorize()` returned `AuthorizationOutcome.REQUIRE_APPROVAL`, `Orchestrator.route_request()` enriched the request payload with `_security_requires_approval = True` and continued dispatching to the target capability. Capabilities (such as `WorkCapability`) were unaware of this flag and executed sensitive operations (such as `work.cancel`) immediately without user approval.
2. **Payload Mutability & Parameter Tampering (VULN-02):** The `Request` dataclass is frozen, but its `payload` field is a mutable Python `dict`. Modifying key-value pairs in-place bypassed dataclass immutability and enabled post-authorization tampering.
3. **Work Step Execution Context Loss / Confused Deputy (VULN-03):** When `WorkService` dispatched steps via `_invoke_capability()`, it constructed requests without actor metadata, causing the Orchestrator to default the caller to an unprivileged anonymous user, breaking authorization for multi-step tasks.

## Decision
1. **Enforce REQUIRE_APPROVAL in Orchestrator:**
   - If an authorization decision evaluates to `REQUIRE_APPROVAL`, the Orchestrator immediately halts execution and returns a structured `Response(success=False, data={"security_decision": "require_approval", "reason": decision.reason}, error="Authorization requires human approval: ...")`.
   - Work dispatch does not occur until approval confirmation is formally supplied.
2. **Payload Snapshot Immutability:**
   - In `Orchestrator.route_request()`, make a defensive, deep snapshot of the payload before evaluating policy rules and dispatching, ensuring the exact evaluated parameters are passed to capability invocation without post-check tampering.
3. **Actor Context Preservation in Work Execution:**
   - Add optional `initiating_actor: ActorIdentity | None` metadata to `Work` and pass this originating actor down into `WorkService._invoke_capability()` to ensure multi-step workflows maintain caller authority without losing security context.

## Consequences
- **Positive:**
  - Prevents unapproved execution of sensitive/destructive operations.
  - Eliminates parameter tampering between authorization and capability dispatch.
  - Preserves legitimate actor authority during multi-step work workflows.
- **Backward Compatibility:**
  - All existing capabilities, contracts, and test scenarios remain compatible.
