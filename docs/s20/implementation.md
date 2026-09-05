# S20 Implementation Notes

## Files Created

| File | Purpose |
|------|---------|
| `core/contracts/security.py` | ActorIdentity, ActorType, AuthorizationRequest, AuthorizationDecision, AuthorizationOutcome, SecurityEvent, SecurityEventType, SYSTEM_ACTOR |
| `core/security/__init__.py` | Package init, public API |
| `core/security/policy.py` | PolicyRule, PolicyEngine, create_default_policy() |
| `core/security/service.py` | SecurityService with event logging |
| `core/security/events.py` | SecurityEventLog for observability |
| `tests/test_s20_security.py` | 43 tests across 8 test classes |

## Files Modified

| File | Change |
|------|--------|
| `core/orchestration/orchestrator.py` | Added optional `security_service` parameter; authorization check in `route_request()` |
| `core/contracts/__init__.py` | Added security contract re-exports |

## Default Policy Rules

| Priority | Actor | Action Pattern | Outcome |
|----------|-------|---------------|---------|
| 100 | SYSTEM | `*` | ALLOW |
| 50 | USER | `work.cancel` | REQUIRE_APPROVAL |
| 50 | USER | `work.redirect` | REQUIRE_APPROVAL |
| 50 | USER | `work.take_over` | REQUIRE_APPROVAL |
| 50 | USER | `work.delete` | REQUIRE_APPROVAL |
| 10 | USER | `*` | ALLOW |
| 50 | AGENT | `work.cancel` | REQUIRE_APPROVAL |
| 50 | AGENT | `work.redirect` | REQUIRE_APPROVAL |
| 50 | AGENT | `work.take_over` | DENY |
| 10 | AGENT | `*` | ALLOW |
| — | * | * | DENY (default) |

## Key Design Decisions

1. **Enforcement at Orchestrator** — single dispatch point
2. **SYSTEM_ACTOR default** — backward compat, no S17-S19 changes
3. **`_actor` in payload** — avoids modifying frozen Request dataclass
4. **Fail-closed policy** — default DENY when no rule matches
5. **S18 separation** — security DENY cannot be bypassed by S18 approval
