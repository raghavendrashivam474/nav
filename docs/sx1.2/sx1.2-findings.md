# Sx1.2 — Vulnerability Findings

This document catalogs the confirmed security vulnerabilities discovered during the adversarial analysis phase of the Sx1.2 Capability & Execution Boundary sprint.

---

## FINDING-01: REQUIRE_APPROVAL Results in Direct Execution (Critical)

### Attack Path
1. A standard USER requests a sensitive operation (e.g., `work.cancel`).
2. The Orchestrator queries `SecurityService.authorize()`.
3. The deterministic policy matches the rule and returns `AuthorizationOutcome.REQUIRE_APPROVAL`.
4. The Orchestrator enriches the request payload with `_security_requires_approval = True`.
5. The Orchestrator continues to call `capability.invoke(request)`.
6. The capability executes immediately, bypassing the approval requirement.

### Evidence
Reproduced in `test_atk_03_and_10_require_approval_must_not_execute_immediately`.

### Root Cause
The Orchestrator's routing logic does not halt execution on a `REQUIRE_APPROVAL` outcome. It expects the downstream capability to handle the flag, but `WorkCapability` is entirely unaware of the security plane's outcome and executes the action immediately.

### Remediation
Halt execution in the Orchestrator on `REQUIRE_APPROVAL`. Return an unsuccessful response containing the decision context and indicating that the request is pending administrative or human approval.

---

## FINDING-02: Frozen Request Payload Dictionary Mutability (High)

### Attack Path
1. A request is created with a harmless payload (e.g., `action: status`, `work_id: work_123`).
2. The Orchestrator authorizes this harmless action.
3. Before execution, the payload dictionary is modified in-place:
   ```python
   request.payload["action"] = "cancel"
   ```
4. The capability executes the mutated action (cancel) under the authorization of the original harmless action (status).

### Evidence

Reproduced in test_atk_04_05_payload_parameter_tampering.

### Root Cause

The Request dataclass is marked frozen=True, which prevents reassignment of fields (e.g., request.payload = ...). However, the payload field itself is a standard Python dict, which is fully mutable. Modifying the dictionary key-value pairs does not trigger an AttributeError.

### Remediation

Convert the payload dictionary to an immutable mapping proxy or perform a deep copy and replacement inside the Orchestrator before authorization, ensuring that the payload evaluated by the policy is identical to the one dispatched to the capability.

## FINDING-03: Work Subsystem Context Loss & Anonymous Execution (High)

### Attack Path

1. An authorized user triggers a multi-step Work item.
2. The first step executes and invokes a downstream capability using        
   WorkService._invoke_capability().
3. The service instantiates a new Request object for the step.
4. The originating actor identity is completely lost during this step instantiation.
5. The Orchestrator receives the step request, finds no actor context, and defaults to anonymous USER.
6. The policy denies the operation, causing a failure even if the originating user was 
   fully authorized.

### Evidence

Reproduced in test_atk_08_work_step_execution_context_loss_confused_deputy.

### Root Cause

Work and WorkStep records do not capture or persist the identity of the actor who authorized them. When the execution engine resolves steps, it cannot pass the authorizing context down, resulting in execution context loss.

### Remediation

Update Work and step structures to capture the initiating actor context and propagate this context into WorkService._invoke_capability.
