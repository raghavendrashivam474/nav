# S20 Reconnaissance Notes

## 1. Where is the current capability invocation boundary?

`Orchestrator.route_request()` → `CapabilityRegistry.get()` →
`Capability.invoke(request)`. This is the single dispatch point for
all capability calls routed through the Orchestrator.

## 2. Where can an action enter NAV?

- Interaction layer (`interfaces/interaction/`)
- Voice interface (`interfaces/voice/`)
- Direct Orchestrator invocation
- Direct `WorkService` method calls (bypasses Orchestrator)

## 3. Can Work actions be invoked without passing through Interaction?

**Yes.** `WorkService` methods are public. The Orchestrator can be
called directly. Many tests call `WorkService` directly.

## 4. Where should authorization be enforced?

At `Orchestrator.route_request()`, before capability dispatch. This
protects all Orchestrator-mediated paths. Direct service calls remain
a known gap for future sprints.

## 5. What existing contracts can carry actor identity?

`Request.payload` dict can carry `_actor` data. `NavContext.UserContext`
has `user_id` but is not in the dispatch path.

## 6. Does the Capability abstraction need an actor/request context?

No. The `Capability.invoke(request)` protocol remains unchanged.
Security wraps the Orchestrator, not the capability.

## 7. Can authorization be introduced without breaking the Capability protocol?

Yes. The Orchestrator checks authorization before calling
`capability.invoke()`. The Capability class is untouched.

## 8. Should authorization wrap capability execution or be invoked by the Orchestrator?

Orchestrator-invoked, before dispatch. This keeps capabilities
unaware of security.

## 9. How should ALLOW, DENY, and REQUIRE_APPROVAL be represented?

`AuthorizationOutcome` enum with three values. `AuthorizationDecision`
dataclass carries outcome plus context (actor, action, resource, reason).

## 10. Which existing tests prove current execution behavior?

`test_s17_work.py`, `test_s18_*.py`, `test_s19_*.py` — 518 tests
at baseline.

## 11. What happens to existing tests if a default identity is required?

Nothing. `SYSTEM_ACTOR` default preserves all existing behavior.
All 518 tests pass unchanged.

## 12. How can backward compatibility be preserved?

`SecurityService.authorize()` defaults to `SYSTEM_ACTOR` when no actor
is provided. Orchestrator only checks when `security_service` is
configured (optional constructor parameter, defaults to `None`).
