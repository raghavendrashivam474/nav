# Aryntra Blackbox

## Sx1.2 — Capability & Execution Boundary Hardening

### Post-Sprint Engineering & Security Report

**Project:** Aryntra Blackbox
**Sprint:** Sx1.2
**Theme:** Capability & Execution Boundary Hardening
**Status:** COMPLETE
**Security Sequence:** Sx1
**Primary Boundary:** Authorization → Capability → Execution

---

# 1. Executive Summary

Sx1.2 was the second adversarial security sprint in the Aryntra Blackbox sequence.

Where Sx1.1 concentrated on **Identity & Authority**, Sx1.2 moved one boundary deeper into NAV's execution architecture:

```text
Identity
   ↓
Authentication / Trust
   ↓
Authorization / Policy
   ↓
[ Sx1.2 boundary ]
Capability
   ↓
Execution
```

The central security question was:

> **Can an actor that has legitimately passed authorization controls bypass, mutate, misuse, or escape the capability and execution boundaries they were authorized to use?**

The answer at the beginning of the sprint was **yes**.

The adversarial campaign identified weaknesses across the authorization-to-execution boundary, including three confirmed vulnerabilities:

1. **REQUIRE_APPROVAL execution escape — Critical**
2. **Frozen Request payload mutability / post-authorization parameter tampering — High**
3. **Work execution actor-context loss / confused-deputy exposure — High**

All three were reproduced through exploit-oriented tests, remediated through targeted architectural changes, and covered by permanent regression tests.

The sprint also investigated a broader set of capability and execution attack families, including direct capability invocation, direct service invocation, capability acquisition, capability impersonation, authorization-context loss, capability composition, SYSTEM authority containment, and resource ownership confusion.

The resulting architecture now provides substantially stronger binding between:

```text
authorized identity
        +
authorized action
        +
authorized resource
        +
authorized parameters
        +
authorized execution context
        ↓
actual execution
```

Sx1.2 therefore establishes a significantly stronger **Authorization → Capability → Execution boundary** while intentionally retaining certain internal-process trust boundaries as documented architectural constraints rather than introducing unnecessary security complexity.

---

# 2. Sprint Objective

Sx1.2 was designed to attack the execution side of the security boundary rather than merely re-test Sx1.1's identity controls.

The primary objective was:

> Determine whether an actor that has legitimately passed identity and authorization controls can bypass, misuse, extend, or escape the capability and execution boundaries they were authorized to use.

The core invariant under investigation was:

> **Authorized identity/action/resource/parameters/authority must remain bound to actual execution.**

This required examining not only whether authorization returned the correct decision, but whether that decision remained meaningful all the way through capability dispatch and state mutation.

---

# 3. Scope

The sprint examined the following architectural areas:

* Orchestrator dispatch
* Security authorization boundary
* Capability Registry
* Capability retrieval and invocation
* WorkCapability
* WorkService
* Work execution and nested capability invocation
* Work persistence
* SQLite serialization
* Human interaction control path
* Request payload handling
* Authorization/execution context propagation
* Capability composition
* SYSTEM authority propagation
* Resource/action binding

The primary implementation areas affected were:

```text
core/orchestration/orchestrator.py
capabilities/work/capability.py
capabilities/work/service.py
capabilities/work/sqlite_repo.py
interfaces/interaction/work_control.py
```

The sprint also added and updated adversarial regression coverage.

---

# 4. Initial Architectural Findings

The initial reconnaissance identified an important architectural distinction:

```text
Authorization Plane
        │
        │  authorization decision
        ▼
Orchestrator
        │
        │  capability dispatch
        ▼
Execution Plane
        │
        ├── Capability
        │
        └── Service
```

Authorization was concentrated at the Orchestrator boundary, while capability and service implementations did not independently possess the full authorization decision.

This produced several important observations.

## 4.1 Authorization was centralized

Authorization occurred at:

```text
Orchestrator.route_request()
```

The capability itself did not receive the complete `AuthorizationDecision`.

This meant the Orchestrator represented the primary policy enforcement point.

## 4.2 Direct capability and service access existed

The investigation confirmed that components could directly obtain or invoke:

* capability objects
* WorkService methods

without passing through the Orchestrator.

This was classified as an **internal trust boundary / architectural weakness**, rather than automatically treating it as an externally exploitable vulnerability.

This distinction was deliberate.

The Blackbox objective is not:

> Add authorization checks everywhere because authorization exists somewhere.

It is:

> Add enforcement where the actual threat model requires it.

The sprint therefore documented these boundaries rather than unnecessarily duplicating security mechanisms across every internal object.

## 4.3 Authorization context did not naturally survive dispatch

The authorization decision was discarded at the capability boundary.

Consequently, downstream execution had limited visibility into:

* actor identity
* actor type
* trust level
* authorization result
* precise authorization context

This became important when examining nested Work execution.

## 4.4 Frozen Request did not imply frozen payload

The Request object itself was frozen, but its payload was a mutable Python dictionary.

Therefore:

```python
request.payload["action"] = "cancel"
```

could mutate the request after authorization.

This created a classic authorization/execution binding problem:

```text
Authorize:
    action = status
    resource = A

Execute:
    action = cancel
    resource = B
```

The Request object's `frozen=True` status therefore provided only shallow immutability.

---

# 5. Threat Model

Sx1.2 evaluated 14 attack families.

| ID     | Attack Family                     | Primary Boundary                |
| ------ | --------------------------------- | ------------------------------- |
| ATK-01 | Direct Capability Invocation      | Orchestrator bypass             |
| ATK-02 | Direct Service Invocation         | Capability bypass               |
| ATK-03 | Action Substitution               | Authorization/execution binding |
| ATK-04 | Resource Substitution             | Resource binding                |
| ATK-05 | Parameter Tampering               | Request integrity               |
| ATK-06 | Capability Impersonation          | Registry integrity              |
| ATK-07 | Privileged Capability Acquisition | Capability possession           |
| ATK-08 | Confused Deputy                   | Nested execution authority      |
| ATK-09 | Authorization Context Loss        | Context propagation             |
| ATK-10 | Authorization Result Manipulation | Approval enforcement            |
| ATK-11 | Failure / Exception Escape        | Failure containment             |
| ATK-12 | Capability Composition            | Composed authority              |
| ATK-13 | SYSTEM Capability Boundary        | Privilege containment           |
| ATK-14 | Resource Ownership Confusion      | Resource authorization          |

The attack campaign intentionally included both concrete exploit attempts and architectural/prospective threats.

---

# 6. Confirmed Vulnerabilities

## 6.1 VULN-01 — REQUIRE_APPROVAL Execution Escape

**Severity:** Critical
**Status:** FIXED

### Attack

A standard USER submitted a sensitive operation such as:

```text
work.cancel
```

The security policy correctly returned:

```text
REQUIRE_APPROVAL
```

However, the Orchestrator previously continued dispatching the request.

The resulting flow was:

```text
USER request
    ↓
SecurityService
    ↓
REQUIRE_APPROVAL
    ↓
payload enriched with approval-required flag
    ↓
Capability.invoke()
    ↓
ACTION EXECUTES
```

The security decision therefore failed to control execution.

### Root Cause

The Orchestrator treated `REQUIRE_APPROVAL` as information to pass downstream rather than as an execution gate.

`WorkCapability` was not responsible for interpreting the security-plane decision.

Therefore the security plane could correctly identify that approval was required while the execution plane proceeded anyway.

### Remediation

The Orchestrator now explicitly intercepts:

```text
AuthorizationOutcome.REQUIRE_APPROVAL
```

and halts execution unless the request contains the expected verified human approval context.

The resulting flow is:

```text
REQUIRE_APPROVAL
       ↓
STOP EXECUTION
       ↓
return structured pending/unsuccessful response
       ↓
no capability invocation
```

### Security Significance

This restores the fundamental invariant:

> **A security decision requiring approval must be an execution barrier, not merely metadata.**

---

# 7. VULN-02 — Frozen Request Payload Mutability

**Severity:** High
**Status:** FIXED

### Attack

The Request object was frozen, but its payload remained mutable.

An attacker or cooperating component could therefore alter:

```python
request.payload["action"]
request.payload["work_id"]
```

after authorization.

For example:

```text
Authorized:
    action = status
    work_id = A

Mutated:
    action = cancel
    work_id = B

Executed:
    cancel(B)
```

### Root Cause

`frozen=True` protects field reassignment but does not recursively freeze mutable objects stored inside fields.

Therefore:

```text
Request immutability
        ≠
Payload immutability
```

### Remediation

The Orchestrator now takes a defensive deep snapshot of the payload before authorization/execution processing.

This ensures that the payload used for the authorization decision is bound to the payload dispatched for execution.

### Security Significance

The remediation strengthens the invariant:

```text
authorized request
        ==
executed request
```

for the relevant request payload state.

This closes the identified post-authorization action/resource/parameter substitution path.

---

# 8. VULN-03 — Work Execution Context Loss

**Severity:** High
**Status:** FIXED

### Attack

A Work item initiated by an authorized actor could execute multiple downstream steps.

During nested execution:

```text
Actor
  ↓
Work
  ↓
WorkStep
  ↓
WorkService
  ↓
Capability
```

the initiating actor identity was lost when the downstream Request was constructed.

The Orchestrator therefore received a step request without the originating authority context.

This could produce:

* unintended authorization failures
* anonymous execution
* confused-deputy conditions
* incorrect authority attribution

### Root Cause

Work and WorkStep state did not retain the initiating actor identity.

When execution later resolved a step, there was no authoritative actor context available to propagate.

### Remediation

The Work lifecycle now captures the initiating actor in:

```text
work.metadata["initiating_actor"]
```

The WorkService extracts this context during step execution and propagates it into the downstream request.

SQLite serialization was also extended to support the persisted actor structures.

### Security Significance

Authority now survives the Work lifecycle:

```text
Initiating Actor
      ↓
Work
      ↓
WorkStep
      ↓
Downstream Request
      ↓
Capability Execution
```

This substantially reduces context-loss and confused-deputy risk in composite Work execution.

---

# 9. Architectural Hardening

The three confirmed vulnerabilities required targeted changes rather than a redesign of NAV's security architecture.

## 9.1 Orchestrator became an actual execution gate

The Orchestrator now performs more than:

```text
authorize → dispatch
```

It effectively performs:

```text
normalize
   ↓
snapshot
   ↓
authorize
   ↓
interpret decision
   ↓
gate execution
   ↓
dispatch
```

This is an important distinction.

The Orchestrator is not merely an authorization query point; for protected requests it is an enforcement boundary.

## 9.2 Execution context is explicitly propagated

The Work subsystem now preserves initiating actor information across lifecycle transitions.

This prevents execution from silently changing identity semantics simply because the request crossed an internal service boundary.

## 9.3 Persistence supports security context

Because actor context is now part of Work execution state, SQLite serialization was updated to safely represent:

* ActorIdentity
* dataclasses
* Enum values

This ensures that the security context is not lost merely because execution state crosses the persistence boundary.

## 9.4 Human approval remains distinct from authorization

The sprint maintains the architectural distinction between:

```text
Authorization
```

and:

```text
Human Approval
```

A policy `DENY` remains a denial.

Human approval is not a mechanism for overriding a denial.

The new approval gate instead handles the specific:

```text
REQUIRE_APPROVAL
```

state.

---

# 10. Attack Results

The 14 attack families produced the following broad outcomes.

### Confirmed and remediated

* ATK-03 — Action Substitution
* ATK-04 — Resource Substitution
* ATK-05 — Parameter Tampering
* ATK-08 — Confused Deputy
* ATK-10 — Authorization Result Manipulation

These map directly or indirectly to the three confirmed vulnerabilities.

### Blocked / existing defenses

* ATK-06 — Capability Impersonation
* ATK-11 — Failure / Exception Escape

Existing registry and Orchestrator containment mechanisms were sufficient for the tested cases.

### Architectural / trust-boundary findings

* ATK-01 — Direct Capability Invocation
* ATK-02 — Direct Service Invocation
* ATK-07 — Capability Reference Acquisition

These remain constrained by the internal-process trust model rather than being treated as independent external security boundaries.

### Potential / future attack surface

* ATK-12 — Capability Composition
* ATK-13 — SYSTEM Capability Boundary
* ATK-14 — Resource Ownership Confusion

These received targeted analysis and regression coverage, with deeper enforcement reserved for cases where the evolving architecture requires it.

---

# 11. Adversarial Test Coverage

Sx1.2 introduced:

```text
tests/test_sx1_2_capability_execution.py
```

The suite is explicitly organized around ATK-01 through ATK-14.

The tests cover:

* direct capability access
* direct service access
* action substitution
* resource substitution
* parameter tampering
* capability impersonation
* capability acquisition
* actor-context propagation
* authorization context
* approval-gate integrity
* exception containment
* capability composition
* SYSTEM authority containment
* resource separation

The dedicated adversarial suite passed successfully.

---

# 12. Verification Results

Final sprint verification reported:

```text
Total regression:
756 passed
0 failed
1 skipped
```

Additional verification:

```text
Sx1.2 adversarial suite:
5 dedicated boundary regression tests passing

Ruff:
100% clean

Mypy:
100% clean
116 source files checked
0 errors
```

The sprint also produced:

```text
ADR-0015:
Sx1.2 Capability & Execution Boundary Hardening
```

and the complete Sx1.2 documentation set:

```text
sx1.2-recon.md
sx1.2-threats.md
sx1.2-findings.md
sx1.2-implementation.md
sx1.2-speculative-attacks.md
sx1.2-residual-security-risks.md
sx1.2-completion-report.md
```

---

# 13. Residual Risk

Sx1.2 did not attempt to claim that the entire capability/execution architecture is universally secure.

The residual register intentionally preserves unresolved future boundaries.

## RR-01 — Direct WorkService Invocation

**Classification:** BLOCKED / Internal Trust
**Severity:** Low in current in-process architecture

Direct WorkService access remains possible to trusted internal components.

This is currently treated as an architectural trust boundary rather than duplicated authorization enforcement.

If NAV moves toward hostile plugin isolation, process isolation, or remote execution, this assumption must be revisited.

## RR-02 — Identity Provenance

**Classification:** OPEN
**Severity:** High if remotely exposed

Current actor propagation establishes structured identity context but does not constitute cryptographic proof of identity provenance.

Future distributed/remote environments may require stronger identity mechanisms.

## RR-03 — Capability Registry Tampering

**Classification:** BLOCKED
**Severity:** Low in current protected runtime

Duplicate registration protection prevents the tested capability impersonation scenario.

Runtime integrity remains a separate future consideration.

## RR-04 — Direct Capability Reference Invocation

**Classification:** BLOCKED / Internal Trust
**Severity:** Low in-process

Possession of a capability reference does not itself bypass Orchestrator authorization when requests are routed through the protected path.

Direct invocation remains an internal trust assumption.

## RR-05 — Distributed Authority Propagation

**Classification:** FUTURE
**Severity:** High*

Multi-device or distributed NAV execution will require stronger authority propagation semantics.

Potential future controls include cryptographically verifiable identity/state origin.

## RR-06 — Complex Capability Composition

**Classification:** POTENTIAL
**Severity:** Medium

Asynchronous and increasingly complex workflows may create side effects that are not adequately represented by simple step-level authorization.

## RR-07 — Step Payload Schema Injection

**Classification:** POTENTIAL
**Severity:** Medium

Future planner-generated or model-generated step payloads may require stronger schema validation and explicit taint handling.

---

# 14. Speculative Future Attack Surface

Three important future attack classes were identified.

## SATK-01 — Asynchronous Workflow Token Stalling

An authorization decision may be generated at:

```text
T0
```

while execution occurs at:

```text
T1
```

after policy, actor trust, or resource state has changed.

The current architecture primarily uses synchronous in-memory execution.

Future asynchronous workflows may require:

* authorization tokens
* TTLs
* step-level revalidation
* policy-version binding

## SATK-02 — Capability Result Manipulation

Outputs from one capability may eventually become inputs to another.

This creates a potential chain:

```text
Capability A output
        ↓
planner / evaluator
        ↓
Capability B input
```

Future security controls may need:

* explicit data provenance
* taint tracking
* schema validation
* output sanitization
* capability-specific input contracts

## SATK-03 — Multi-Device Authority Desynchronization

Distributed NAV instances may eventually attempt to propagate authority across devices.

This creates a potential problem where:

```text
Environment A:
    authority granted

Environment B:
    authority claimed
```

without cryptographic proof that the authority originated from a trusted source.

Future work may require signatures around:

* ActorIdentity
* StateOrigin
* authorization assertions

---

# 15. Why the Sprint Did Not Fully Close Every Boundary

An important architectural decision in Sx1.2 was **not to equate every trust boundary with a vulnerability**.

For example:

```text
Direct WorkService invocation
```

is technically possible.

That does not automatically mean the system has an exploitable remote security vulnerability.

The current assumption is that the Python process and its trusted internal components constitute a security boundary.

Adding authorization logic independently to every service method would introduce:

* duplicated policy enforcement
* increased change amplification
* inconsistent authorization semantics
* additional security complexity
* potential divergence between security layers

without evidence that the current threat model requires it.

Therefore the sprint chose:

> **Evidence-backed enforcement over security-mechanism proliferation.**

This is consistent with the broader Blackbox philosophy.

---

# 16. Architectural Impact

Sx1.2 does not replace the S20 security architecture.

Instead, it strengthens its enforcement boundary.

Before:

```text
Identity
   ↓
Authorization
   ↓
Orchestrator
   ↓
Capability
   ↓
Service
```

The authorization decision could lose meaning between the Orchestrator and actual execution.

After hardening:

```text
Identity
   ↓
Authorization
   ↓
Request Snapshot
   ↓
Decision Enforcement
   ↓
Verified Execution Context
   ↓
Capability
   ↓
Service
   ↓
State Mutation
```

For Work execution:

```text
Initiating Actor
       ↓
     Work
       ↓
 Work Metadata
       ↓
   Work Step
       ↓
Downstream Request
       ↓
 Orchestrator
       ↓
Authorization
       ↓
 Capability
```

The architecture therefore has stronger continuity between authorization and execution.

---

# 17. Git / Engineering Delivery

Sx1.2 was committed in capability-oriented chunks rather than as a single undifferentiated implementation commit.

Final local history:

```text
2c6b620
fix(sx1.2): enforce approval execution boundary

7b9c7fd
fix(sx1.2): preserve actor context across work execution

8164ac5
test(sx1.2): add capability boundary adversarial suite

0dcdb15
docs(sx1.2): record capability boundary hardening
```

At completion:

```text
Branch: main
Working tree: clean
Local branch: 4 commits ahead of origin/main
```

The sprint implementation, tests, and documentation are therefore committed and internally clean.

The next release ceremony should separately perform:

```text
push implementation commits
        ↓
verify origin/main
        ↓
create canonical Sx1.2 security tag
        ↓
push tag
        ↓
freeze Sx1.2
```

The Git release/tag operation is intentionally treated as a separate finalization step rather than being implicitly assumed by the sprint completion report.

---

# 18. Senior Engineering Assessment

Sx1.2 successfully demonstrated that the original authorization boundary was **not sufficient by itself**.

The security plane could make a correct decision while the execution plane could still:

* execute a `REQUIRE_APPROVAL` operation
* consume mutated parameters
* lose the originating actor context

These were genuine architectural security failures because they broke the relationship between authorization and actual execution.

The most important result of Sx1.2 is therefore not any individual patch.

It is the architectural principle established by the sprint:

> **Authorization is only meaningful if its identity, action, resource, parameters, and authority remain bound to the operation that ultimately executes.**

Sx1.2 strengthened that binding in three critical areas:

```text
Decision
   ↓
Execution Gate

Request
   ↓
Immutable Execution Snapshot

Actor
   ↓
Persistent Work Context
```

This materially improves NAV's security posture while preserving the modularity and low-change-amplification characteristics of the existing architecture.

---

# 19. Final Status

**Sx1.2 — Capability & Execution Boundary Hardening: COMPLETE**

### Completion criteria

* [x] Reconnaissance completed
* [x] Threat model completed
* [x] 14 attack families defined
* [x] Confirmed vulnerabilities reproduced
* [x] Critical approval escape fixed
* [x] High-severity parameter tampering fixed
* [x] High-severity execution-context loss fixed
* [x] Capability/service trust boundaries assessed
* [x] Adversarial regression suite implemented
* [x] Regression suite passing
* [x] Ruff clean
* [x] Mypy clean
* [x] Residual risk register documented
* [x] Speculative attack analysis documented
* [x] ADR-0015 documented
* [x] Formal completion report documented
* [x] Capability-wise Git commits created
* [x] Working tree clean

**Engineering conclusion:**

Sx1.2 has achieved its intended objective of materially hardening NAV's **Authorization → Capability → Execution boundary** against the tested adversarial classes.

The remaining risks are explicitly documented rather than hidden, and the architecture is ready for the next Blackbox security boundary campaign.
