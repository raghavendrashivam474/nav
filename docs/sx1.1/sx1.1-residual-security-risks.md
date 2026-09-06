# Sx1.1 — Residual Security Risks

**Project:** Aryntra Blackbox
**Security Sprint:** Sx1.1 — Identity & Authority
**Status:** Open-risk register / future attack surface
**Scope:** Identity, authority, authorization, and adjacent execution boundaries

---

## 1. Purpose

This document records security weaknesses, architectural weaknesses, and potential future attack surfaces that remain after the Sx1.1 Identity & Authority hardening campaign.

The purpose is **not** to imply that every item below is currently exploitable.

Each item is classified according to the evidence currently available:

* **FIXED** — an attack was demonstrated and the vulnerable behavior was remediated and regression-tested.
* **BLOCKED** — the attack was investigated and the current architecture prevented it.
* **OPEN** — a genuine architectural/security weakness remains and has not been remediated.
* **POTENTIAL** — a plausible attack class has been identified, but current evidence does not establish exploitability.
* **FUTURE** — primarily relevant when NAV gains additional capabilities, persistence, distribution, or asynchronous execution.

Sx1.1 should not be reopened solely to eliminate speculative risk. Future changes should be driven by demonstrated attack paths, architectural evidence, or a clearly justified change in NAV's threat model.

---

# 2. Current Security Baseline

Sx1.1 and Sx1.1-B established and validated the following boundary:

```text
Untrusted Input
      ↓
Actor / Authority Interpretation
      ↓
Security Authorization
      ↓
Human Approval where required
      ↓
Capability
      ↓
Execution
```

The campaign demonstrated two exploitable authorization-boundary vulnerabilities:

1. Untrusted `_actor` payload injection could claim `SYSTEM`.
2. Omitted `_actor` values could fall through to `SYSTEM_ACTOR`.

Both were remediated at the Orchestrator boundary.

Sx1.1-B additionally validated:

* authority laundering resistance
* fail-closed behavior during authorization exceptions
* frozen security request/identity contracts
* confused-deputy resistance for tested AGENT actions
* metadata/context authority isolation
* deterministic policy resolution
* capability registration collision resistance
* deterministic repeated authorization decisions

These protections are covered by adversarial regression tests.

---

# 3. Residual Risk Register

| ID    | Risk / Attack Surface                                                | Classification         | Severity     | Likely Follow-up               |
| ----- | -------------------------------------------------------------------- | ---------------------- | ------------ | ------------------------------ |
| RR-01 | Direct `WorkService` invocation bypassing Orchestrator authorization | **OPEN**               | High*        | Sx1.2                          |
| RR-02 | Identity provenance / trusted identity creation                      | **OPEN**               | High*        | Future Identity/Auth           |
| RR-03 | SecurityService substitution or compromise                           | **POTENTIAL**          | High*        | Security infrastructure        |
| RR-04 | Privileged capability acquisition outside authorized dispatch        | **POTENTIAL**          | High*        | Sx1.2                          |
| RR-05 | `SYSTEM_ACTOR` propagation outside intended trust boundary           | **POTENTIAL**          | High*        | Sx1.2 / multi-device           |
| RR-06 | Authorization-to-execution identity/action/resource mismatch         | **POTENTIAL**          | High*        | Sx1.2                          |
| RR-07 | Replay or reuse of stale authorization decisions                     | **POTENTIAL / FUTURE** | Medium–High* | Async Work / execution         |
| RR-08 | Cross-resource authorization confusion                               | **POTENTIAL**          | High*        | Sx1.2                          |
| RR-09 | Security policy/configuration integrity                              | **FUTURE**             | High*        | Policy/security infrastructure |

* Severity represents potential impact if the boundary becomes attacker-reachable. It is not a claim of current exploitability.

---

# 4. RR-01 — Direct WorkService Authorization Bypass

## Description

S20 establishes authorization at the Orchestrator dispatch boundary:

```text
Caller
  ↓
Orchestrator
  ↓
SecurityService
  ↓
Capability
  ↓
WorkService
```

However, `WorkService` remains independently callable.

Conceptually, another path may exist:

```text
Caller
  ↓
WorkService
  ↓
State-changing operation
```

This creates an architectural distinction between:

> "The normal NAV execution path is security-gated"

and:

> "Every privileged side effect is intrinsically security-gated."

The latter has not yet been established.

## Current Evidence

Sx1.1 investigated direct `WorkService` invocation.

No current deployment-level exploitability was established.

Therefore this is classified as an **open architectural weakness**, rather than a confirmed exploitable vulnerability.

## Risk

If an attacker-controlled component can obtain a `WorkService` reference, it may potentially bypass the Orchestrator's authorization boundary.

## Current Decision

Do not modify `WorkService` solely to improve the Sx1.1 score.

Carry the question into the Capability & Execution boundary investigation.

---

# 5. RR-02 — Identity Provenance

## Description

Sx1.1 hardens the handling of actor information crossing an untrusted input boundary.

It does not establish a complete answer to:

> Who is authorized to create or establish a trusted `ActorIdentity`?

The distinction is:

```text
Identity representation
        ≠
Identity provenance
```

A correctly formed `ActorIdentity` object is not, by itself, proof that the claimed actor actually controls or owns that identity.

## Current Evidence

The current local architecture does not provide a production-grade authentication or cryptographic identity-establishment system.

This was outside Sx1.1 scope.

## Risk

The risk becomes substantially more important when NAV introduces:

* multiple devices
* remote communication
* portable environments
* external integrations
* persistent accounts
* networked capabilities

## Current Decision

Record as an open architectural concern.

Do not introduce authentication infrastructure into Sx1.1 without a demonstrated requirement.

---

# 6. RR-03 — SecurityService Substitution or Compromise

## Attack Hypothesis

If a malicious or compromised component can replace, intercept, monkey-patch, or otherwise control the security service:

```text
Malicious Component
       ↓
SecurityService substitution
       ↓
ALLOW
       ↓
Orchestrator
       ↓
Privileged Capability
```

the correctness of the policy engine alone would no longer protect the system.

## Current Evidence

Sx1.1-B verified fail-closed behavior of the intended SecurityService under induced authorization failures.

It did not establish protection against compromise or replacement of the security implementation itself.

## Classification

**POTENTIAL**

This is primarily a trusted-runtime / dependency-integrity problem rather than a policy-rule problem.

## Future Investigation

Evaluate:

* security-service lifecycle
* dependency injection trust
* runtime mutation
* component integrity
* privileged service registration
* plugin isolation
* trusted runtime boundaries

---

# 7. RR-04 — Privileged Capability Acquisition

## Attack Hypothesis

Sx1.1 validated capability registration collision resistance.

A deeper question remains:

> Can an attacker obtain a reference to an existing privileged capability and invoke it without passing through the authorized dispatch boundary?

The attack is different from malicious capability registration.

```text
Attacker
   ↓
Acquire legitimate capability reference
   ↓
Direct invocation
   ↓
Privileged operation
```

## Classification

**POTENTIAL**

## Follow-up

This should be a primary attack class for Sx1.2.

The investigation should determine whether capability possession itself constitutes authority or whether capability invocation remains bound to an authorization context.

---

# 8. RR-05 — SYSTEM_ACTOR Propagation

## Attack Hypothesis

Sx1.1 blocks untrusted payloads from simply claiming SYSTEM authority.

A deeper question is:

> Where can a legitimate `SYSTEM_ACTOR` originate, and through which boundaries can it propagate?

Potential failure mode:

```text
Trusted SYSTEM Context
        ↓
Unintended propagation
        ↓
Lower-trust component
        ↓
Privileged operation
```

## Classification

**POTENTIAL**

## Follow-up

Investigate:

* SYSTEM actor creation
* SYSTEM actor lifetime
* propagation through context
* background work
* plugin boundaries
* multi-device boundaries
* serialization/deserialization
* autonomous workflows

---

# 9. RR-06 — Authorization-to-Execution Mismatch

Authorization is meaningful only if the values authorized are the same values ultimately executed.

The required invariant is:

```text
Authorized Identity  = Executing Identity
Authorized Action    = Executed Action
Authorized Resource  = Affected Resource
```

A future execution layer could accidentally create a confused-deputy condition:

```text
Authorize(A, cancel, Work-A)
             ↓
Execution(A, cancel, Work-B)
```

or:

```text
Authorize(A)
     ↓
internal execution uses B
```

## Classification

**POTENTIAL**

## Follow-up

Test this at the capability and execution boundary rather than modifying Sx1.1's identity contracts prematurely.

---

# 10. RR-07 — Replay / Stale Authorization

Sx1.1-B established deterministic repeated authorization behavior.

Determinism does not establish temporal validity.

A future asynchronous system could introduce:

```text
Authorization
     ↓
time passes
     ↓
authority changes
     ↓
old decision reused
     ↓
execution
```

Potential controls may eventually include:

* request binding
* decision binding
* expiration
* nonces
* one-time authorization
* execution-time revalidation

## Classification

**POTENTIAL / FUTURE**

This is currently low relevance because the existing architecture does not implement a distributed or long-lived authorization-token model.

---

# 11. RR-08 — Cross-Resource Authorization Confusion

Authorization must bind not only to an action but also to the intended resource.

Example:

```text
Authorized:
    work.cancel → Work A

Attempt:
    work.cancel → Work B
```

A policy engine can produce a correct decision while a downstream component incorrectly applies the decision to another resource.

## Classification

**POTENTIAL**

## Follow-up

Exercise resource binding at the capability/execution boundary.

Particular attention should be given to:

* Work IDs
* nested resources
* indirect resource references
* redirected work
* asynchronous execution
* multi-step Work

---

# 12. RR-09 — Policy / Configuration Integrity

The current policy engine is deterministic and its rule ordering has been tested.

A future system may make policies:

* persisted
* user-editable
* synchronized
* plugin-provided
* remotely delivered
* dynamically generated

That creates a different attack surface:

```text
Attacker
   ↓
Policy / configuration modification
   ↓
Legitimate PolicyEngine
   ↓
Legitimate ALLOW
```

The policy engine can therefore remain perfectly correct while operating on compromised policy data.

## Classification

**FUTURE**

This should be addressed only when policy configuration becomes mutable or externally managed.

---

# 13. Findings Explicitly Closed by Sx1.1

The following attack paths were demonstrated and hardened:

### Actor Injection

```text
Untrusted `_actor` dictionary
        ↓
SYSTEM claim
        ↓
Authorization
```

**Status: FIXED**

Untrusted dictionary actor claims are sanitized and downgraded to an unprivileged USER identity.

### Actor Omission

```text
No `_actor`
    ↓
SYSTEM fallback
```

**Status: FIXED**

Missing or invalid actor information no longer implicitly receives SYSTEM authority at the Orchestrator boundary.

### Authorization Exception → Execution

```text
Security failure
       ↓
continued execution
```

**Status: FIXED**

Unexpected authorization exceptions are converted into a failed response and dispatch does not continue.

### Metadata Authority Injection

```text
metadata = {"admin": true}
        ↓
privilege escalation
```

**Status: BLOCKED**

Current policy evaluation does not derive authority from arbitrary metadata.

### AGENT → Human Takeover

**Status: BLOCKED**

Current policy prevents the tested AGENT escalation path.

### Approval → Security Bypass

**Status: BLOCKED**

Human approval does not override a security authorization denial.

---

# 14. Security Boundary Invariants to Preserve

Future development must preserve the following invariants:

```text
Untrusted input
      ↓
must never directly become authority.
```

```text
Model output
      ↓
must never directly become authority.
```

```text
Metadata
      ↓
must never implicitly become authority.
```

```text
Human approval
      ↓
must never override authorization DENY.
```

```text
SYSTEM authority
      ↓
must never originate from untrusted input.
```

```text
Authorization
      ↓
must precede privileged execution.
```

```text
Authorization failure
      ↓
must not result in privileged execution.
```

```text
Authorized identity/action/resource
      ↓
must remain bound to the actual execution.
```

These are security invariants, not implementation details.

---

# 15. Sx1.1 Freeze Position

Sx1.1 should be considered **implementation-complete** with respect to the demonstrated Identity & Authority vulnerabilities.

The existence of residual attack surfaces does not, by itself, justify reopening the sprint.

The correct progression is:

```text
Sx1.1
Identity & Authority
      ↓
Demonstrated vulnerabilities fixed
      ↓
Residual risks recorded
      ↓
Sx1.2
Capability & Execution Boundary
      ↓
Attack the next trust boundary
```

The objective is not to make every possible future vulnerability disappear before continuing.

The objective is to maintain an explicit security ledger in which every meaningful risk is:

```text
Discovered
   ↓
Classified
   ↓
Tested
   ↓
Fixed
   OR
   ↓
Consciously deferred
   ↓
Assigned to a future attack surface
```

---

# 16. Final Risk Statement

Sx1.1 materially strengthened NAV's Identity & Authority boundary and removed the demonstrated privilege-escalation paths identified during the Blackbox campaign.

The remaining risks primarily concern boundaries **around** authorization rather than the demonstrated correctness of the current policy decisions themselves.

The most important next questions are therefore:

1. Can a caller reach privileged capability execution without Orchestrator authorization?
2. Can a caller obtain or invoke a privileged capability directly?
3. Can trusted authority propagate into a lower-trust context?
4. Can authorization be separated from the resource/action actually executed?
5. Can the security infrastructure itself be substituted or compromised?

These questions should guide subsequent Blackbox work.

**Sx1.1 is frozen with residual risks explicitly recorded rather than silently ignored.**
