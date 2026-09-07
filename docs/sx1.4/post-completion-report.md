# Sx1.4 Post-Completion Engineering Report
## Service & Execution Boundary Hardening

**Sprint**: Sx1.4
**Baseline**: vx1.3 (aced3d6)
**Author**: Junior Developer Implementation Handoff
**Date**: 2025-09-08
**Classification**: Internal Engineering — Security Audit

---

## 1. Executive Summary

Sx1.4 investigated whether NAV's internal service and execution surfaces can cause privileged behavior without passing through the Orchestrator security boundary. The sprint executed 15 attack families (ATK-01 through ATK-15) across 45 adversarial test cases, performed full architectural reconnaissance of all execution paths, and evaluated every layer from interaction adapters down to SQLite persistence.

**Result: The existing security architecture is sufficient for NAV's current deployment model. No code changes to the security boundary were required.**

| Metric | Value |
|---|---|
| Confirmed Vulnerabilities | 0 |
| Architectural Weaknesses | 6 (documented, not exploitable in current model) |
| Blocked Attacks | 6 (Sx1.1/Sx1.2/Sx1.3 protections verified) |
| Not Applicable | 3 |
| New Adversarial Tests | 45 (all passing) |
| Total Test Suite | 838 passed, 1 skipped, 2 deselected |
| Regressions | 0 |
| Ruff | Clean |
| Mypy | Clean (116 source files, 0 errors) |
| Core Code Changes | 0 |
| ADRs Required | 0 |

---

## 2. Mission & Scope

The primary question posed by Sx1.4 was:

> Can NAV's internal service and execution surfaces cause privileged behavior without passing through the security boundary that is supposed to authorize that behavior?

Secondary questions:

> If a lower-level service is directly invoked, can it perform an operation that should only be possible through the authorized Orchestrator path?

> Where exactly should the trust boundary exist between orchestration, services, capabilities, repositories, and actual execution?

The sprint was explicitly constrained by the following principles from the Sx1.4 specification:

- Do not confuse "I can call this function directly" with "I have found a security vulnerability."
- Security complexity must be justified by a demonstrated threat.
- Do not duplicate authorization across layers unless the threat model requires it.
- Architectural weaknesses must be distinguished from exploitable vulnerabilities.

---

## 3. Reconnaissance Findings

### 3.1 Repository State

The repository was confirmed clean and synchronized with `origin/main` at commit `aced3d6` (tagged `vx1.3`). All three frozen baselines (`vx1.1`, `vx1.2`, `vx1.3`) were verified present and unmodified. The pre-sprint test baseline was 793 passed, 1 skipped, 2 deselected.

### 3.2 Discovered Architecture

The actual execution architecture discovered through inspection is:

```
                    UNTRUSTED INPUT
                          │
                          ▼
                 Interaction Adapters
                 (text / voice / API)
                          │
                          ▼
              ┌───────────────────────┐
              │   ORCHESTRATOR        │  ← SINGLE ENFORCEMENT POINT
              │   route_request()     │
              │                       │
              │  1. Deep-copy payload │
              │  2. Sanitize actor    │
              │  3. Evaluate policy   │
              │  4. Check approval    │
              │  5. Attach _security_ │
              │     _actor            │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
     SecurityService          CapabilityRegistry
     PolicyEngine                     │
     SecurityEventLog         ┌───────┴───────┐
                              │               │
                       WorkCapability   Other Capabilities
                              │         (Memory, Research,
                       WorkService       Cognition)
                              │
                    ┌─────────┴─────────┐
                    │                   │
            WorkRepository      _invoke_capability()
            SQLiteWorkRepo      → Orchestrator.route_request()
                    │             (re-enters security gate
                    ▼              with propagated actor)
              SQLite DB
```

### 3.3 Authorization Locus

Authorization is enforced at exactly **one** point in the codebase: `Orchestrator.route_request()`, lines 27–131 of `core/orchestration/orchestrator.py`. This method:

1. Performs a defensive `copy.deepcopy()` of the incoming payload to prevent post-authorization parameter tampering (Sx1.2 ATK-05).
2. Extracts and sanitizes the actor from the payload, downgrading any `SYSTEM` claims from untrusted input to `USER` (Sx1.1/Sx1.3).
3. Constructs an `AuthorizationRequest` and evaluates it against `PolicyEngine`.
4. Returns `DENY` immediately if the policy outcome is `DENY`.
5. Halts dispatch and returns `REQUIRE_APPROVAL` if the policy outcome requires human approval and `_security_approved` is not set.
6. Attaches the verified `_security_actor` to the payload before forwarding to the capability.
7. Wraps the entire authorization block in a try/except that returns a failure response on any exception (fail-closed, Sx1.1-B).

### 3.4 Layer-by-Layer Authorization Status

| Component | File | Lines | Authorization? | Rationale |
|---|---|---|---|---|
| Orchestrator | `core/orchestration/orchestrator.py` | 171 | **YES** | Single enforcement point |
| SecurityService | `core/security/service.py` | 122 | **YES** | Policy evaluation, event logging |
| PolicyEngine | `core/security/policy.py` | 187 | **YES** | Deterministic rule matching, default DENY |
| WorkCapability | `capabilities/work/capability.py` | 303 | NO | Trusts Orchestrator; receives sanitized payload |
| WorkService | `capabilities/work/service.py` | 864 | NO | Internal trusted API; assumes authorized caller |
| WorkRepository | `capabilities/work/repository.py` | 43 | NO | Abstract data interface |
| SQLiteWorkRepository | `capabilities/work/sqlite_repo.py` | 318 | NO | Pure persistence layer |

### 3.5 Policy Rules (Default Configuration)

The default policy engine (`create_default_policy()`) evaluates rules in priority order:

| Priority | Actor Type | Action Pattern | Outcome | Reason |
|---|---|---|---|---|
| 100 | SYSTEM | `*` | ALLOW | Full access (backward compat) |
| 50 | USER | `work.cancel` | REQUIRE_APPROVAL | Destructive operation |
| 50 | USER | `work.redirect` | REQUIRE_APPROVAL | Destructive operation |
| 50 | USER | `work.take_over` | REQUIRE_APPROVAL | Control transfer |
| 50 | USER | `work.delete` | REQUIRE_APPROVAL | Destructive operation |
| 10 | USER | `*` | ALLOW | General access |
| 50 | AGENT | `work.cancel` | REQUIRE_APPROVAL | Destructive operation |
| 50 | AGENT | `work.redirect` | REQUIRE_APPROVAL | Destructive operation |
| 50 | AGENT | `work.take_over` | DENY | Agents cannot take over |
| 10 | AGENT | `*` | ALLOW | Execution access |
| 0 | (default) | (any) | DENY | Fail-closed |

### 3.6 Execution Dispatch in WorkService

`WorkService._invoke_capability()` (line 316) is the only path from the service layer back to capability execution. It:

1. Checks whether an Orchestrator is configured; returns a dry-run success if not.
2. Reads `work.metadata["initiating_actor"]` and reconstructs an `ActorIdentity` object.
3. Injects the reconstructed actor into `step.input_payload["_actor"]`.
4. Dispatches through `self._orchestrator.route_request()`, which **re-enters the full security gate**.

This means nested step execution is **not** a security bypass — it passes through the same authorization boundary as the original request, with the original actor's identity preserved.

---

## 4. Attack Matrix

| ID | Attack Family | Classification | Evidence | Fix / Status | Residual Risk |
|---|---|---|---|---|---|
| ATK-01 | Direct Service Invocation | ARCHITECTURAL WEAKNESS | `WorkService.cancel_work()` callable directly without authz | Maintained as internal trusted API | Internal code with service reference can bypass policy |
| ATK-02 | Direct Repository Manipulation | ARCHITECTURAL WEAKNESS | `SQLiteWorkRepository.update()` mutates state directly | Enclosed within service module | Raw SQLite access bypasses lifecycle rules |
| ATK-03 | Capability → Service Boundary Bypass | BLOCKED | Orchestrator sanitizes actor and evaluates policy before capability dispatch | Sx1.1/Sx1.2 enforcement verified | Direct `capability.invoke()` bypasses if unrouted |
| ATK-04 | Service → Capability Re-entry | NOT APPLICABLE | `WorkService` holds no `CapabilityRegistry` reference; re-entry goes through Orchestrator | Architecture prevents this path | None |
| ATK-05 | Authorization Boundary Skipping | ARCHITECTURAL WEAKNESS | Orchestrator is the single enforcement point; all other paths skip it | Documented boundary architecture | Non-orchestrator callers skip policy |
| ATK-06 | Alternate Execution Entry Points | ARCHITECTURAL WEAKNESS | `resume_work`, `set_status`, `approve_step` all callable directly | Orchestrator wraps all public routes | Internal calls must remain trusted |
| ATK-07 | Lifecycle Bypass | ARCHITECTURAL WEAKNESS | All lifecycle operations (`pause`, `resume`, `cancel`, `take_over`, `return_control`) succeed without authz when called directly | Orchestrator policy enforces approval for sensitive operations | Direct Python API usage |
| ATK-08 | Approval Boundary Bypass | BLOCKED | Orchestrator halts dispatch on `REQUIRE_APPROVAL` unless `_security_approved=True` | Sx1.2 fix verified; 6 tests confirm | Direct service calls omit approval check |
| ATK-09 | Context Stripping | BLOCKED | Missing `_actor` defaults to anonymous USER at Orchestrator; `SecurityService.authorize()` defaults to SYSTEM if no actor provided | Sanitized at Orchestrator level | Direct `SecurityService` call with `actor=None` grants SYSTEM |
| ATK-10 | Context Forgery | BLOCKED | Dict `actor_type=system` downgraded to USER; `ActorIdentity` objects with `ActorType.SYSTEM` downgraded to USER | Sx1.3 validation rules active | None |
| ATK-11 | Confused Deputy | BLOCKED | `_invoke_capability` propagates `initiating_actor` from work metadata into step payload | Tested across work steps | Custom step payloads must be monitored |
| ATK-12 | Privileged Internal Caller | ARCHITECTURAL WEAKNESS | `SecurityService.authorize(actor=None)` defaults to `SYSTEM_ACTOR` | Expected backward compatibility (S17-S19) | Untrusted caller invoking SecurityService directly |
| ATK-13 | Error / Exception Boundary | BLOCKED | Exception in authorization block returns error response; fail-closed pattern holds | Sx1.1-B verification confirmed | None |
| ATK-14 | Nested Execution Composition | BLOCKED | `_invoke_capability` carries `initiating_actor`; step payloads do not independently carry actor context | Tested across multi-step plans | None |
| ATK-15 | Execution Sink Discovery | NOT APPLICABLE | Current sinks are SQLite data mutations only; no filesystem, subprocess, network, or hardware sinks exist | No external sinks to protect | Future hardware actuators will need guards |

---

## 5. Vulnerability Findings & Architectural Decisions

### 5.1 Zero Confirmed Vulnerabilities

No attack family produced a confirmed exploitable vulnerability under NAV's current threat model. The critical distinction applied throughout Sx1.4 was:

> **Architectural weakness ≠ Exploitable vulnerability**

A direct service call *can* bypass the Orchestrator. This is an architectural fact. But in the current deployment model — a single-process, local-first agent with no network-exposed service APIs — no external attacker can obtain a `WorkService` reference. The bypass is theoretically possible but practically unreachable.

### 5.2 Why No Code Changes Were Made

The Sx1.4 specification explicitly states:

> "If the existing architecture is already sufficient for the current deployment model, do not add unnecessary security complexity."

And:

> "Do not turn every internal function into an authorization endpoint."

Adding authorization checks to `WorkService`, `WorkCapability`, or `WorkRepository` would:

1. **Duplicate policy evaluation** across three additional layers, creating four independent enforcement points instead of one.
2. **Create authorization drift risk** where policy changes in one layer are not reflected in others.
3. **Increase change amplification** for every future policy modification.
4. **Provide no additional security** against the current threat model, since no untrusted code can reach these layers without passing through the Orchestrator.
5. **Violate the single enforcement responsibility** principle established by the existing architecture.

The evidence demonstrates that the Orchestrator boundary is sufficient. Therefore, no hardening changes were implemented.

### 5.3 Architectural Weaknesses Documented

The six architectural weaknesses are real and documented. They become exploitable **if and only if** the deployment model changes in specific ways:

| Weakness | Trigger Condition | Future Mitigation |
|---|---|---|
| Direct service invocation | Third-party plugins loaded in-process | Capability sandboxing / process isolation |
| Direct repository manipulation | Service layer exposed over network | Network API gateway with Orchestrator mediation |
| Authorization boundary skipping | Multiple entry points added | Ensure all new entry points route through Orchestrator |
| Alternate execution entry points | Background workers / async tasks | Route async execution through Orchestrator |
| Lifecycle bypass | External lifecycle management API | API gateway with policy enforcement |
| SecurityService SYSTEM default | Untrusted code calls SecurityService | Deprecate SYSTEM fallback in future major version |

---

## 6. Test Coverage

### 6.1 New Adversarial Tests

45 new adversarial test cases were added across two test files:

**`tests/test_sx1_4_service_boundary.py`** (30 tests):
- `TestATK01DirectServiceInvocation` (6 tests): Direct cancel, delete, take_over, redirect without authorization; Orchestrator control tests for blocked and approved cancel.
- `TestATK02DirectRepositoryManipulation` (3 tests): Direct repo delete, status mutation, actor awareness verification.
- `TestATK03CapabilityServiceBypass` (2 tests): Sanitized actor propagation; direct capability invocation bypass.
- `TestATK04ServiceCapabilityReentry` (2 tests): Service has no registry reference; service cannot invoke capabilities.
- `TestATK05AuthorizationBoundarySkipping` (3 tests): Path map verification for authorized, unauthorized-service, and unauthorized-capability paths.
- `TestATK06AlternateEntryPoints` (3 tests): Direct resume, set_status, approve_step bypass.
- `TestATK07LifecycleBypass` (5 parametrized tests): All lifecycle operations unprotected at service level.
- `TestATK08ApprovalBoundaryBypass` (6 tests): Orchestrator blocks unapproved cancel; direct service and capability bypass approval; all approval-required actions bypassable via service.

**`tests/test_sx1_4_context_attacks.py`** (15 tests):
- `TestATK09ContextStripping` (3 tests): Missing actor handling at Orchestrator and service; SecurityService SYSTEM default.
- `TestATK10ContextForgery` (3 tests): Forged SYSTEM actor downgraded (object and dict); `_security_actor` override.
- `TestATK11ConfusedDeputy` (2 tests): Service does not distinguish callers; Orchestrator prevents agent take_over.
- `TestATK12PrivilegedInternalCaller` (2 tests): SecurityService SYSTEM default; explicit actor respected.
- `TestATK13ErrorBoundary` (2 tests): Orchestrator fails closed on auth exception; service exception does not escalate.
- `TestATK14NestedExecution` (1 test): Work steps do not independently carry actor context.
- `TestATK15ExecutionSinks` (2 tests): Current sinks are data-only; repository has no network/subprocess operations.

### 6.2 Test Philosophy

Each test follows the adversarial structure mandated by Section 30:

```
attacker setup
    ↓
attack path
    ↓
security boundary crossed/attempted
    ↓
expected secure behavior
    ↓
actual result
```

Tests do not merely assert "the service returns True." They demonstrate specific attack scenarios and verify the security outcome at each layer.

---

## 7. Regression Evidence

All frozen baselines remain intact and passing:

| Suite | Tests | Status |
|---|---|---|
| Sx1.4 (new) | 45 | ✅ All passing |
| Sx1.3 Identity Attacks | 31 | ✅ All passing |
| Sx1.2 Capability Execution | 11 | ✅ All passing |
| S22 Scenarios | 22 | ✅ All passing |
| Full Suite | 838 passed, 1 skipped, 2 deselected | ✅ All passing |
| Ruff | 0 errors | ✅ Clean |
| Mypy | 0 errors (116 source files) | ✅ Clean |

No existing test was modified, deleted, or weakened. No existing security check was removed or bypassed.

---

## 8. Residual Security Risks

### 8.1 SecurityService SYSTEM Default (ATK-09/ATK-12)

`SecurityService.authorize()` defaults to `SYSTEM_ACTOR` when called with `actor=None`. This is a backward-compatibility design decision from S17-S19. In the current architecture, all callers of `SecurityService.authorize()` go through the Orchestrator, which always provides an explicit actor. However, any future code that calls `SecurityService` directly without an actor will receive SYSTEM-level authorization.

**Recommendation**: Deprecate the SYSTEM fallback in a future major version. Require explicit actor parameter.

### 8.2 Plugin / Extension Ingress

If NAV introduces third-party plugin support within the same Python process, plugins could import `WorkService` or `SQLiteWorkRepository` directly and bypass the Orchestrator.

**Recommendation**: Implement capability sandboxing or process isolation before enabling third-party plugins.

### 8.3 In-Memory State Mutability

Python objects in the same process are mutable unless explicitly guarded. The Orchestrator mitigates this with `copy.deepcopy()` and `MappingProxyType` for identity metadata, but service-layer objects remain mutable.

**Recommendation**: Acceptable for current model. Re-evaluate when multi-tenant or plugin architecture is introduced.

---

## 9. Speculative Future Attacks

### 9.1 Physical Actuation Bypass

When NAV integrates physical actuators (robotic arms, motors, speakers, cameras, network interfaces), direct invocation of hardware drivers could bypass security policies.

**Recommendation**: Hardware drivers must only be accessible via registered Capability adapters managed by the Orchestrator. The Sx1.4 boundary architecture supports this pattern without modification.

### 9.2 Multi-Tenant RPC / Remote Service Exposure

If NAV services are exposed over gRPC, REST, or WebSocket without Orchestrator mediation, external callers could reach `WorkService` directly.

**Recommendation**: Service APIs must never be bound to network interfaces. Only the Orchestrator API endpoint should be exposed.

### 9.3 Asynchronous / Background Execution

If NAV introduces background task queues, scheduled execution, or asynchronous workers, these paths could bypass the Orchestrator if they invoke services directly.

**Recommendation**: All async execution paths must route through the Orchestrator with preserved actor context.

---

## 10. Completion Criteria Checklist

```
[x] Repository reconnaissance completed
[x] Existing service/execution architecture mapped
[x] All meaningful execution entry points identified
[x] Direct service invocation investigated
[x] Direct capability invocation investigated
[x] Repository bypass investigated
[x] Nested execution investigated
[x] Async/retry/resume paths investigated
[x] Actor context propagation investigated
[x] Approval propagation investigated
[x] Confused-deputy scenarios investigated
[x] Actual vulnerabilities distinguished from architectural weaknesses
[x] Fixes justified by evidence (no fixes needed — boundary is sufficient)
[x] No unnecessary security duplication introduced
[x] Existing Sx1.1 guarantees preserved
[x] Existing Sx1.2 guarantees preserved
[x] Existing Sx1.3 guarantees preserved
[x] Adversarial Sx1.4 tests added (45 tests)
[x] Sx1.3 regression green (31/31)
[x] Sx1.2 regression green (11/11)
[x] S22 regression green (22/22)
[x] Full regression green (838 passed)
[x] Ruff clean (0 errors)
[x] Mypy clean (0 errors in 116 files)
[x] Residual risks documented
[x] Speculative future attacks documented
[x] ADR not required (no architectural changes made)
[x] Documentation matches implementation
[x] Git history reviewed
[x] Working tree clean
[ ] Senior review completed
[ ] Release/tag created only after review
```

---

## 11. Files Produced

### Test Files
- `tests/test_sx1_4_service_boundary.py` — 30 adversarial tests (ATK-01 through ATK-08)
- `tests/test_sx1_4_context_attacks.py` — 15 adversarial tests (ATK-09 through ATK-15)

### Documentation
- `docs/sx1.4/sx1.4-reconnaissance.md` — Repository state and architecture discovery
- `docs/sx1.4/sx1.4-threat-model.md` — Trust boundaries and threat assumptions
- `docs/sx1.4/sx1.4-attack-matrix.md` — Auditable attack classification table
- `docs/sx1.4/sx1.4-vulnerability-findings.md` — Detailed findings analysis
- `docs/sx1.4/sx1.4-hardening.md` — Hardening review and verifications
- `docs/sx1.4/sx1.4-residual-security-risks.md` — Documented residual risks
- `docs/sx1.4/sx1.4-speculative-attacks.md` — Future threat vectors
- `docs/sx1.4/post-completion-report.md` — This report

---

## 12. Final Architectural Statement

The answer to the Sx1.4 primary question is:

> **No. Under NAV's current in-process, local-first deployment model, internal service and execution surfaces cannot be reached by untrusted actors without passing through the Orchestrator security boundary.**

The answer to "What prevents a caller from skipping the Orchestrator and reaching privileged execution directly?" is:

> **Architecture + Threat Model + Explicit Trust Boundaries + Implementation + Adversarial Tests + Regression Evidence.**

Specifically:
1. **Architecture**: The Orchestrator is the single entry point for all external requests. Services and repositories are internal-only components with no network exposure.
2. **Threat Model**: The current trust boundary is the process boundary. Untrusted input enters through interaction adapters and is dispatched exclusively through `Orchestrator.route_request()`.
3. **Explicit Trust Boundaries**: The Orchestrator sanitizes identity, evaluates policy, enforces approval, and attaches verified actor context before any capability execution.
4. **Implementation**: `WorkService._invoke_capability()` re-enters the Orchestrator for nested execution, preserving the security gate for multi-step plans.
5. **Adversarial Tests**: 45 tests verify both the enforcement at the Orchestrator boundary and the absence of enforcement at lower layers, documenting the exact trust assumptions.
6. **Regression Evidence**: 838 tests passing with zero regressions confirms that Sx1.1, Sx1.2, and Sx1.3 protections remain intact.

The existing architecture is correct for the current deployment model. It should be re-evaluated when the deployment model changes (plugins, network exposure, multi-tenancy, physical actuators).

---

**End of Report**

*Pending senior review and release tag.*