# Sx1.2 — Capability & Execution Boundary Recon & Threat Model

## 1. System Inspection Overview

We inspected the files of Aryntra NAV's core capability and execution layers. The architecture reveals a distinct gap between the **Authorization Plane** (handled at the Orchestrator) and the **Execution Plane** (handled inside Capability and Service implementations).

### Architectural Invariant Status
Our inspection answered the 12 key reconnaissance questions:
1. **Capability Registration:** Plain dictionary registration in CapabilityRegistry without access control. Duplicate registration is prevented, but retrieval is open to anyone.
2. **Capability Retrieval:** No authorization or identity checks. Possession is unrestricted once a reference to the registry is obtained.
3. **Capability Invocation:** Orchestrator calls .invoke(request). Capabilities receive raw payload dicts but have no access to the AuthorizationDecision itself.
4. **Authorization Location:** Exclusively at Orchestrator.route_request(). If _security_service is omitted, the system defaults to completely unauthenticated pass-through execution.
5. **Authorization Context Survival:** **Does not survive.** The decision is discarded; capabilities execute with no knowledge of the actor type, trust level, or specific authorization bounds.
6. **Execution Without Orchestrator:** **Yes.** Any component can directly instantiate or invoke Capability.invoke() or WorkService methods.
7. **Capability to Service Path:** WorkCapability holds a direct, un-gated reference to WorkService. It passes payload parameters without secondary authorization checks.
8. **Direct Service Invocation:** **Yes.** WorkService is a standard service with public methods, executing state mutations without performing or requesting authorization.
9. **Resource/Action Parameter Binding:** Derived from equest.payload at authorization time, but since payload is a mutable dictionary, parameters can be mutated after authorization check but before capability execution.
10. **Payload Mutation:** The Request dataclass is frozen, but its payload field is a mutable dict. Modifying key-value pairs in-place bypasses frozen immutability.
11. **Capability Reference Acquisition:** Unrestricted through registry lookup.
12. **Exception Escape:** Unhandled capability exceptions are captured by Orchestrator's try-catch block and returned as unsuccessful Responses.

---

## 2. Threat & Attack Matrix

| Attack ID | Target | Description | Expected Status (Pre-Fix) | Target Status (Post-Hardening) |
|---|---|---|---|---|
| **ATK-01** | Orchestrator Bypass | Directly invoke WorkCapability.invoke() bypassing Orchestrator. | **VULNERABLE** | **BLOCKED** / **DOCUMENTED TRUST BOUNDARY** |
| **ATK-02** | Service Bypass | Directly call WorkService state-changing methods bypassing Orchestrator. | **VULNERABLE** | **BLOCKED** / **DOCUMENTED TRUST BOUNDARY** |
| **ATK-03** | Action Substitution | Tamper with request parameters to swap authorized harmless actions for sensitive actions. | **VULNERABLE** | **FIXED** |
| **ATK-04** | Resource Substitution | Authorize against Work ID 'A', execute against Work ID 'B'. | **VULNERABLE** | **FIXED** |
| **ATK-05** | Parameter Tampering | Mutate dictionary contents inside frozen Request object in-flight. | **VULNERABLE** | **FIXED** |
| **ATK-08** | Confused Deputy | Make WorkService._invoke_capability run nested steps with elevated/unintended authority. | **VULNERABLE** | **FIXED** |
| **ATK-10** | Result Manipulation | Exploit Orchestrator's handling of REQUIRE_APPROVAL where it fails to halt execution. | **VULNERABLE** | **FIXED** |
| **ATK-13** | SYSTEM Escape | Exploit systemic fallback to SYSTEM_ACTOR or leaks of SYSTEM authority. | **VULNERABLE** | **FIXED** |
| **ATK-14** | Resource Ownership | Execute actions on resources owned or restricted to other actors. | **VULNERABLE** | **FIXED** |

