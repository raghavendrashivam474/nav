# Sx1.F — Attack Matrix: 55 Cross-Boundary Adversarial Scenarios

**Sprint:** Sx1.F (Final Aggregate Campaign)  
**Baseline:** `vx1.4`  
**Total Scenarios:** 55  
**Pass Rate:** 100% (55 / 55)

---

## Attack Campaigns Summary

| Campaign | Focus Area | Scenarios | Result |
|---|---|---|---|
| **Campaign A** | Identity → Authorization → Execution | 7 | 7 BLOCKED |
| **Campaign B** | Authorization → Capability → Service | 6 | 6 BLOCKED |
| **Campaign C** | Approval → Execution | 8 | 8 BLOCKED |
| **Campaign D** | Work → Persistence → Resume | 7 | 6 BLOCKED, 1 ARCH WEAKNESS |
| **Campaign E** | Nested Work → Nested Capability | 4 | 4 BLOCKED |
| **Campaign F** | Cross-Boundary Context Corruption | 6 | 6 BLOCKED |
| **Campaign G** | Failure → Partial Mutation → Retry | 5 | 5 BLOCKED |
| **Campaign H** | TOCTOU / State Transition Attacks | 4 | 4 BLOCKED |
| **Campaign I** | Cross-Boundary Replay | 4 | 4 BLOCKED |
| **Campaign J** | Full Multi-Stage Attack Chains | 4 | 4 BLOCKED |

---

## Detailed Attack Scenarios

### Campaign A: Identity → Authorization → Execution

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXA-01 | USER identity claims `system` in payload dict | Demoted to USER; cancel halted for approval | Pass | BLOCKED |
| SXA-02 | Injected `_actor` dictionary during routing | Outbound request receives verified `_security_actor` | Pass | BLOCKED |
| SXA-03 | Mutate frozen `ActorIdentity.metadata` | Raises `TypeError` / immutable proxy | Pass | BLOCKED |
| SXA-04 | Reuse actor across independent requests | Each request evaluated independently | Pass | BLOCKED |
| SXA-05 | AGENT attempts work takeover | Deterministically DENIED by policy | Pass | BLOCKED |
| SXA-06 | Anonymous / missing actor | Defaults to unprivileged USER with trust 0 | Pass | BLOCKED |
| SXA-07 | Forged `ActorIdentity(actor_type=SYSTEM)` | Demoted to USER unless exact singleton | Pass | BLOCKED |

### Campaign B: Authorization → Capability → Service

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXB-01 | Authorize status then attempt cancel | Status ALLOW does not grant cancel authority | Pass | BLOCKED |
| SXB-02 | Resource substitution during auth | Policy evaluates each resource target separately | Pass | BLOCKED |
| SXB-03 | Target non-existent capability | Orchestrator fails closed | Pass | BLOCKED |
| SXB-04 | Creator identity binding | Work captures `initiating_actor` provenance | Pass | BLOCKED |
| SXB-05 | Payload mutation after snapshot | Deepcopy isolates original input dictionary | Pass | BLOCKED |
| SXB-06 | Policy default-deny on unmapped action | Policy engine defaults to DENY (fail-closed) | Pass | BLOCKED |

### Campaign C: Approval → Execution

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXC-01 | Unapproved sensitive action | Dispatch halted with `REQUIRE_APPROVAL` | Pass | BLOCKED |
| SXC-02 | Valid pre-approved request | Proceeds to execution | Pass | BLOCKED |
| SXC-03 | Approval override on DENY rule | DENY cannot be overridden by approval flag | Pass | BLOCKED |
| SXC-04 | Non-boolean truthy approval flag | Orchestrator evaluates boolean strictly | Pass | BLOCKED |
| SXC-05 | Replay approval to different work ID | Rejected; each work ID evaluated individually | Pass | BLOCKED |
| SXC-06 | Step-level approval isolation | Approving step 1 does not approve step 2 | Pass | BLOCKED |
| SXC-07 | Rejected step lifecycle | Step marked FAILED; entire work PAUSED | Pass | BLOCKED |
| SXC-08 | Approval with payload edit | Records `PLAN_REVISED` and audit trail | Pass | BLOCKED |

### Campaign D: Work → Persistence → Resume

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXD-01 | Persisted work roundtrip | State, status, tags reload identically | Pass | BLOCKED |
| SXD-02 | Direct DB status column edit | Row reloads with edited status (no row MAC) | Pass | ARCH WEAKNESS |
| SXD-03 | Resumed work provenance | Resumed work retains original `initiating_actor` | Pass | BLOCKED |
| SXD-04 | Completed step immutability | `revise_plan` rejects mutating completed steps | Pass | BLOCKED |
| SXD-05 | Corrupted DB JSON blob | Raises `JSONDecodeError` rather than bypass | Pass | BLOCKED |
| SXD-06 | Delete work persistence cleanup | Deleted work cannot be retrieved or resumed | Pass | BLOCKED |
| SXD-07 | Resume terminal work | Raises `WorkControlError` | Pass | BLOCKED |

### Campaign E: Nested Work → Nested Capability

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXE-01 | Nested capability re-entry cancel | Child request evaluated against policy; halted | Pass | BLOCKED |
| SXE-02 | Context propagation to nested cap | WorkService propagates actor to child requests | Pass | BLOCKED |
| SXE-03 | Forged SYSTEM parent inheritance | Child cannot inherit fake SYSTEM authority | Pass | BLOCKED |
| SXE-04 | Nested capability failure | Step marked FAILED; error captured cleanly | Pass | BLOCKED |

### Campaign F: Cross-Boundary Context Corruption

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXF-01 | External payload injects `_security_actor` | Sanitized from `_actor`, overriding injection | Pass | BLOCKED |
| SXF-02 | Empty string actor ID | Defaults to anonymous USER | Pass | BLOCKED |
| SXF-03 | Invalid actor type strings (`root`, `admin`) | Coerced to USER | Pass | BLOCKED |
| SXF-04 | Trust level spoofing in dict | Unverified trust level forced to 0 | Pass | BLOCKED |
| SXF-05 | Malformed types (integers, bytes) | Sanitizes safely or fails closed | Pass | BLOCKED |
| SXF-06 | Resource priority resolution | `work_id` prioritized over generic `resource` | Pass | BLOCKED |

### Campaign G: Failure → Partial Mutation → Retry

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXG-01 | Step retry count increment | `retry_step` increments retry count cleanly | Pass | BLOCKED |
| SXG-02 | Retry beyond max retries | Raises `ValueError` ("exhausted retries") | Pass | BLOCKED |
| SXG-03 | Retry non-failed step | Raises `ValueError` ("not in FAILED status") | Pass | BLOCKED |
| SXG-04 | Rejected Orchestrator call | No dirty state persisted to database | Pass | BLOCKED |
| SXG-05 | Plan revision audit trail | Old plan version snapshot preserved in history | Pass | BLOCKED |

### Campaign H: TOCTOU / State Transition Attacks

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXH-01 | Post-request payload tampering | Deepcopy snapshot prevents modification | Pass | BLOCKED |
| SXH-02 | Control actions on terminal work | Terminal work rejects pause, resume, takeover | Pass | BLOCKED |
| SXH-03 | Executable check on paused work | `_check_executable` raises error on paused work | Pass | BLOCKED |
| SXH-04 | In-flight actor metadata immutability | Metadata remains unchanged during routing | Pass | BLOCKED |

### Campaign I: Cross-Boundary Replay

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXI-01 | Approval replay across actions | Pre-approval for cancel does not permit redirect | Pass | BLOCKED |
| SXI-02 | Data blob clone across work items | ID integrity preserved; cannot hijack work ID | Pass | BLOCKED |
| SXI-03 | Request ID replay | Identical `request_id` still evaluated by policy | Pass | BLOCKED |
| SXI-04 | Actor context reuse across capabilities | Policy evaluates each capability independently | Pass | BLOCKED |

### Campaign J: Full Multi-Stage Attack Chains

| ID | Scenario Description | Expected Invariant | Result | Classification |
|---|---|---|---|---|
| SXJ-01 | Full chain: Forged actor → DB → Approval → Terminal resume | Actor demoted, approval enforced, resume blocked | Pass | BLOCKED |
| SXJ-02 | Full chain: Multi-step plan → Modified approval → Revision guard | Payload sanitized, steps audited, completion locked | Pass | BLOCKED |
| SXJ-03 | Full chain: Agent takeover lockout across reload | Agent takeover DENIED before and after reload | Pass | BLOCKED |
| SXJ-04 | Full chain: Fail-closed on security exception | Unhandled policy error fails closed safely | Pass | BLOCKED |