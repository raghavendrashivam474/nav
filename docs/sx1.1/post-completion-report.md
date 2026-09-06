---

# Aryntra Blackbox — Sx1.1 Post-Sprint Report

**Sprint:** Sx1.1 — Identity & Authority Boundary  
**Project:** NAV  
**Branch:** `sprint/sx1.1-identity-authority`  
**Date:** 2026-09-07  
**Author:** Junior Developer (Sx1.1 Assignee)  
**Reviewer:** Senior Developer  

---

## 1. Executive Summary

Sx1.1 executed a structured adversarial campaign against NAV's existing Identity → Authority → Authorization boundary (established in S20, v1.10). The sprint identified **two exploitable vulnerabilities** — one CRITICAL and one HIGH — both residing in the Orchestrator's actor extraction logic. Both were hardened with minimal, surgical changes to a single file (`core/orchestration/orchestrator.py`). Full regression across all 750 existing tests passed without modification to any S17–S25 code.

**Key outcome:** Untrusted callers can no longer escalate to SYSTEM authority through payload injection or actor omission.

---

## 2. Scope & Methodology

### 2.1 What Was Attacked

| Component | File(s) | Role |
|---|---|---|
| Security Contracts | `core/contracts/security.py` | Frozen identity and authorization dataclasses |
| Policy Engine | `core/security/policy.py` | Deterministic rule evaluation, fail-closed |
| Security Service | `core/security/service.py` | Authorization orchestration, event logging |
| Orchestrator | `core/orchestration/orchestrator.py` | Single enforcement boundary for capability dispatch |
| Work Service | `capabilities/work/service.py` | Lifecycle management (known direct-call gap) |
| Work Capability | `capabilities/work/capability.py` | Capability wrapper over WorkService |
| Interaction Layer | `interfaces/interaction/interaction_layer.py` | User-facing dispatch boundary |
| Work Control Adapter | `interfaces/interaction/work_control.py` | Human control action routing |

### 2.2 What Was NOT Modified

Per sprint rules, the following were left untouched unless attack evidence demanded changes:

- All S17–S25 implementation code
- `core/contracts/capability.py`, `core/contracts/work.py`, `core/contracts/context.py`
- `capabilities/work/repository.py`, `capabilities/work/sqlite_repo.py`
- All interface, AI, and external-information subsystems
- All completed sprint history and release tags

### 2.3 Attack Methodology

The sprint followed the prescribed attack-first workflow:

```
Recon → Attack Matrix → Execute Attacks → Classify Findings
    → Research Fixes → Implement Minimal Hardening
    → Re-Execute Attacks → Prove With Regression Tests
```

No fixes were applied until attacks demonstrated concrete exploitable behavior.

---

## 3. Attack Campaign Results

### 3.1 Full Attack Matrix

| ID | Attack | Target | Baseline Result | Post-Hardening |
|---|---|---|---|---|
| ATK-01 | **Payload `_actor` Dictionary Injection** | Orchestrator extraction | ❌ **VULNERABLE** — Attacker gained SYSTEM | ✅ BLOCKED |
| ATK-02 | **Actor Omission → SYSTEM Fallback** | SecurityService default | ❌ **VULNERABLE** — Omission granted root | ✅ BLOCKED |
| ATK-03 | Actor Identity Mutation | `ActorIdentity` frozen contract | ✅ BLOCKED (AttributeError) | ✅ BLOCKED |
| ATK-04 | Trust Level Spoofing (`trust_level=100`) | PolicyEngine evaluation | ✅ BLOCKED (rules match on ActorType) | ✅ BLOCKED |
| ATK-05 | Direct WorkService Invocation | Service-level boundary | ⚠️ ARCHITECTURAL WEAKNESS | ⚠️ DOCUMENTED |
| ATK-06 | Human Approval Override of DENY | S18 vs S20 separation | ✅ BLOCKED (DENY is final) | ✅ BLOCKED |
| ATK-07 | Unknown Action / Fail-Closed | PolicyEngine default | ✅ BLOCKED (DENY) | ✅ BLOCKED |
| ATK-08 | Empty Action String | PolicyEngine matching | ✅ BLOCKED (DENY) | ✅ BLOCKED |
| ATK-09 | Agent → USER Privilege Escalation | Policy rules | ✅ BLOCKED (AGENT takeover = DENY) | ✅ BLOCKED |
| ATK-10 | User Destructive Action Bypass | Policy rules | ✅ BLOCKED (REQUIRE_APPROVAL) | ✅ BLOCKED |

---

## 4. Detailed Findings

### Finding 1: Untrusted Payload Actor Injection (CRITICAL)

**Vulnerability:** The Orchestrator's `route_request()` method extracted `_actor` from `request.payload` and, when it was a `dict`, blindly constructed an `ActorIdentity` with whatever `actor_type` the caller supplied — including `"system"`.

**Attack Path:**
```
Attacker → crafts Request(payload={"_actor": {"actor_type": "system", "trust_level": 100}})
    → Orchestrator.route_request()
    → isinstance(actor_data, dict) == True
    → ActorIdentity(actor_type=ActorType.SYSTEM)
    → SecurityService.authorize(actor=SYSTEM)
    → PolicyEngine matches SYSTEM wildcard → ALLOW
    → Capability invoked with full root privileges
```

**Evidence (pre-fix log):**
```
Security: allow actor=attacker action=destructive.destroy_all resource= reason=Matched policy rule
```

**Root Cause:** The Orchestrator treated untrusted dictionary data in the request payload as a trusted source of identity. There was no validation that the caller was authorized to claim the `SYSTEM` actor type.

**Severity:** CRITICAL — Any untrusted caller with access to the Orchestrator dispatch path could execute any action, including destructive operations, by injecting a single dictionary field.

---

### Finding 2: Actor Omission Elevation to SYSTEM Authority (HIGH)

**Vulnerability:** When `_actor` was absent from `request.payload`, the Orchestrator passed `actor=None` to `SecurityService.authorize()`. The SecurityService's backward-compatibility fallback then substituted `SYSTEM_ACTOR` (full root), granting wildcard ALLOW on all actions.

**Attack Path:**
```
Attacker → crafts Request(payload={"action": "admin_action"})  # no _actor key
    → Orchestrator.route_request()
    → actor_data = None → actor = None
    → SecurityService.authorize(actor=None)
    → effective_actor = SYSTEM_ACTOR
    → PolicyEngine matches SYSTEM wildcard → ALLOW
    → Capability invoked with full root privileges
```

**Evidence (pre-fix log):**
```
Security: allow actor=nav:system action=test_cap.admin_action resource= reason=Matched policy rule
```

**Root Cause:** `SecurityService.authorize()` was designed with a `SYSTEM_ACTOR` fallback for legacy S17–S19 internal callers that predate the security plane. However, the Orchestrator — which is the external-facing dispatch boundary — passed `None` through to this fallback, conflating "legacy internal call" with "unauthenticated external request."

**Severity:** HIGH — Any request entering the Orchestrator without an explicit `_actor` field received full SYSTEM authority. This includes all requests from the Interaction Layer, voice adapter, and any future external API.

---

### Finding 3: Direct WorkService Invocation (ARCHITECTURAL WEAKNESS)

**Observation:** `WorkService` exposes public methods (`pause_work`, `cancel_work`, `take_over`, `delete_work`, etc.) that perform no internal authorization checks. Any code with a reference to the `WorkService` instance can invoke these methods directly, bypassing the Orchestrator's security boundary entirely.

**Analysis:** This is the known gap documented in the S20 completion report. After investigation, I classified it as an **architectural weakness** rather than an exploitable vulnerability in the current deployment model because:

1. `WorkService` is instantiated internally and passed to `WorkCapability`, which is registered with the `Orchestrator`.
2. The Interaction Layer and voice adapters dispatch exclusively through the Orchestrator.
3. No current code path exposes `WorkService` methods to untrusted or model-controlled callers without Orchestrator mediation.
4. The `WorkService._invoke_capability()` method itself routes through the Orchestrator for step execution.

**Recommendation:** This should be revisited in a future sprint if NAV introduces plugin architectures, multi-tenant access, or any mechanism where untrusted code obtains a `WorkService` reference. Potential mitigations include service-level authorization decorators or a request-context object carrying verified identity.

---

## 5. Hardening Implementation

### 5.1 Changes Made

**Single file modified:** `core/orchestration/orchestrator.py`

The actor extraction block in `route_request()` was replaced with a three-tier sanitization strategy:

```python
# Tier 1: Trusted in-memory ActorIdentity objects — preserved as-is
if isinstance(actor_data, ActorIdentity):
    actor = actor_data

# Tier 2: Untrusted payload dictionaries — sanitized
elif isinstance(actor_data, dict):
    raw_type = str(actor_data.get("actor_type", "user")).lower()
    if raw_type == ActorType.SYSTEM.value:
        actor_type = ActorType.USER  # Downgrade unverified SYSTEM claim
    else:
        try:
            actor_type = ActorType(raw_type)
        except ValueError:
            actor_type = ActorType.USER
    actor = ActorIdentity(
        actor_id=str(actor_data.get("actor_id", "anonymous")),
        actor_type=actor_type,
        trust_level=0,  # Unverified payloads cannot assert trust
    )

# Tier 3: Omitted/invalid — default to unprivileged user
else:
    actor = ActorIdentity(
        actor_id="anonymous",
        actor_type=ActorType.USER,
        trust_level=0,
    )
```

### 5.2 What Was NOT Changed (and Why)

| Component | Decision | Rationale |
|---|---|---|
| `SecurityService.authorize()` | Untouched | Legacy `SYSTEM_ACTOR` fallback is still needed for direct internal calls (e.g., S20 backward-compat tests). The fix belongs at the Orchestrator boundary, not the service. |
| `PolicyEngine` | Untouched | Policy rules are correct and deterministic. The vulnerability was in identity construction, not policy evaluation. |
| `ActorIdentity` contract | Untouched | Already frozen and well-designed. No changes needed. |
| `WorkService` | Untouched | Architectural weakness documented but not exploitable in current deployment. Adding service-level auth would be a larger architectural change requiring an ADR. |
| S18 approval logic | Untouched | S18/S20 separation is intact and tested. |

### 5.3 Backward Compatibility Verification

The existing S20 test `test_default_actor_backward_compat` continues to pass because:
- It sends a request with `payload={"action": "t"}` (no `_actor`).
- Post-hardening, this defaults to `ActorType.USER` instead of `SYSTEM`.
- The default policy grants `USER` wildcard `ALLOW` at priority 10 for general actions.
- Therefore `resp.success is True` still holds for non-restricted actions.

The existing S20 test `test_system_actor_default_for_legacy` continues to pass because:
- It calls `SecurityService.authorize()` directly (not through Orchestrator).
- The `SYSTEM_ACTOR` fallback in `SecurityService` is unchanged.

---

## 6. Test Results

### 6.1 Adversarial Suite (`tests/test_sx1_1_identity_authority.py`)

```
10/10 PASSED
- TestActorSpoofingAndInjection (4 tests)
- TestDirectServiceBoundary (1 test)
- TestPrivilegeEscalation (2 tests)
- TestApprovalGateSeparation (1 test)
- TestFailClosedBoundary (2 tests)
```

### 6.2 Full Regression Suite

```
750 passed, 1 skipped, 2 deselected in 40.35s
```

- Zero regressions across S1–S25.
- All S20 security invariants intact.
- All S18 approval integration tests intact.
- All S22 end-to-end scenario tests intact.

### 6.3 Linters

```
ruff check . → Clean
mypy core capabilities → Clean
```

---

## 7. Security Properties Proven

| Property | Statement | Evidence |
|---|---|---|
| P1 | Identity does not equal authority | ATK-03, ATK-04: Forging identity objects or trust scores does not grant privileges beyond policy rules. |
| P2 | Actor type cannot be casually escalated | ATK-01: Payload dicts claiming SYSTEM are downgraded to USER. |
| P3 | Authorization happens before execution | Orchestrator returns DENY response before `capability.invoke()` is reached. |
| P4 | Authorization cannot be bypassed through normal dispatch | All Orchestrator-routed requests encounter the security boundary. |
| P5 | Approval cannot override DENY | ATK-06: Security DENY halts dispatch; S18 approval gate is never reached. |
| P6 | Unknown authority fails closed | ATK-07, ATK-08: Unmatched actions return DENY. |
| P7 | SYSTEM authority is protected | ATK-01, ATK-02: Untrusted callers cannot manufacture SYSTEM identity through Orchestrator. |
| P8 | Direct internal boundaries are understood | ATK-05: WorkService direct-call gap documented as architectural weakness with clear exposure assessment. |

---

## 8. Architectural Decisions

No formal ADR was created because the hardening was a localized fix within the existing architecture, not a structural change. However, the following decision should be recorded:

**Decision:** The Orchestrator is the authoritative identity-sanitization boundary for all externally-routed requests. `SecurityService`'s `SYSTEM_ACTOR` fallback is reserved for direct internal calls only.

**Rationale:** Separating the trust boundary (Orchestrator) from the policy engine (SecurityService) allows legacy internal code to function while preventing untrusted external requests from inheriting root privileges.

---

## 9. Recommendations for Future Sprints

1. **Sx1.2 — Direct Service Boundary Hardening:** Consider adding optional authorization decorators to `WorkService` methods to close the architectural gap documented in Finding 3. This would require an ADR and careful backward-compatibility analysis.

2. **Sx1.3 — Authentication Layer:** NAV currently has authorization (what can this identity do?) but no authentication (is this identity who it claims to be?). If NAV moves toward multi-user, multi-device, or network-exposed deployment, an authentication mechanism will be required to make the `ActorIdentity` claims trustworthy at the network boundary.

3. **Request Context Object:** Consider introducing a first-class `RequestContext` object (as proposed in the S20 report) that carries verified identity through the dispatch chain, replacing the current `_actor` payload convention entirely.

4. **Security Audit Logging:** The `SecurityEventLog` exists but is in-memory only. For production deployment, consider persistent audit logging of all authorization decisions.

---

## 10. Artifacts Produced

| Artifact | Location |
|---|---|
| Adversarial test suite | `tests/test_sx1_1_identity_authority.py` |
| Hardened Orchestrator | `core/orchestration/orchestrator.py` |
| Recon report | `docs/sx1/sx1.1-recon.md` |
| Threat matrix | `docs/sx1/sx1.1-threats.md` |
| Findings report | `docs/sx1/sx1.1-findings.md` |
| Implementation notes | `docs/sx1/sx1.1-implementation.md` |
| Completion report | `docs/sx1/sx1.1-completion-report.md` |

---

## 11. Definition of Done Checklist

- [x] Existing S20 identity model understood
- [x] Existing authorization model understood
- [x] Existing Orchestrator enforcement understood
- [x] Existing S18 approval boundary understood
- [x] Direct WorkService boundary investigated
- [x] `_actor` propagation investigated
- [x] `SYSTEM_ACTOR` behavior investigated
- [x] Actor spoofing tested
- [x] Actor-type escalation tested
- [x] SYSTEM impersonation tested
- [x] Trust-level manipulation tested
- [x] `_actor` injection tested
- [x] Authorization bypass tested
- [x] Direct service bypass tested
- [x] Approval bypass tested
- [x] Unknown input / fail-closed behavior tested
- [x] Every successful attack documented
- [x] Severity assigned
- [x] Root cause identified
- [x] Evidence-backed fixes implemented
- [x] Existing valid behavior preserved
- [x] No unnecessary architecture rewritten
- [x] Previously successful attacks now blocked
- [x] Legitimate authorized actions still work
- [x] S18 approval semantics still work
- [x] S20 security invariants still hold
- [x] Full NAV regression passes (750/750)
- [x] Ruff passes
- [x] Mypy passes
- [x] Documentation complete

---

**Sx1.1 is complete.** The Identity & Authority boundary is hardened, evidence-backed, and regression-validated. Ready for Sx1.2 when you are. 🔒