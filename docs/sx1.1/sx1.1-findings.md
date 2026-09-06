# Sx1.1 Security Findings & Classification

## Finding 1: Untrusted Payload Actor Injection & Spoofing
- **Classification:** Exploitable Vulnerability
- **Severity:** CRITICAL
- **Preconditions:** Caller provides a dictionary in `request.payload["_actor"]` with `actor_type: "system"`.
- **Attack Path:** Caller crafts request -> Orchestrator blindly parses dict -> instantiates `ActorIdentity(actor_type=ActorType.SYSTEM)` -> `SecurityService` grants full wildcard access.
- **Observed Behavior:** External/untrusted callers gained full SYSTEM privileges.
- **Remediation:** In `Orchestrator.route_request()`, untrusted payload dictionaries claiming `system` are downgraded to `ActorType.USER` with `trust_level=0`. Only trusted in-memory `ActorIdentity` objects are preserved.

## Finding 2: Actor Omission Elevation to SYSTEM Authority
- **Classification:** Exploitable Vulnerability
- **Severity:** HIGH
- **Preconditions:** Caller sends a request omitting `_actor` in `payload`.
- **Attack Path:** Caller sends payload without `_actor` -> Orchestrator passes `actor=None` -> `SecurityService.authorize()` defaults to `SYSTEM_ACTOR` -> Wildcard ALLOW granted.
- **Observed Behavior:** Unauthenticated capability calls received root SYSTEM authority.
- **Remediation:** Orchestrator sets default identity for omitted/unauthenticated requests to `ActorIdentity(actor_id="anonymous", actor_type=ActorType.USER, trust_level=0)` when evaluating policy. Direct `SecurityService.authorize()` calls without actor retain backward compatibility for internal legacy invocations.

## Finding 3: Direct WorkService Invocation Bypassing Security
- **Classification:** Architectural Weakness / Accepted Internal Boundary
- **Severity:** LOW (Internal Context) / ARCHITECTURAL WEAKNESS
- **Preconditions:** Code with direct access to Python object instances invokes `work_service.pause_work()`, etc.
- **Attack Path:** Direct in-process function invocation bypassing `Orchestrator.route_request()`.
- **Analysis:** `WorkService` is an internal subsystem component designed to be fronted by `WorkCapability` and `Orchestrator`. NAV's security perimeter is enforced at the `Orchestrator` dispatch boundary. Direct in-memory invocation is restricted to internal engine loops and test fixtures.
