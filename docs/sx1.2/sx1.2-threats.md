# Sx1.2 — Threat Model & Attack Matrix

This document defines the comprehensive threat matrix and attack families evaluated during the Sx1.2 Capability & Execution Boundary hardening campaign.

---

## 1. Threat & Attack Families

### ATK-01 — Direct Capability Invocation
- **Threat:** An attacker invokes a registered capability directly, bypassing the Orchestrator's security check.
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_01_direct_capability_invocation_bypasses_orchestrator`.
- **Mitigation Strategy:** Document as a trusted-layer boundary; capability objects should verify that their caller possesses legitimate authority or enforce execution parameters.

### ATK-02 — Direct Service Invocation
- **Threat:** An attacker bypasses the capability layer entirely and calls the underlying `WorkService` state-changing methods directly.
- **Pre-Remediation Status:** **VULNERABLE** (Architectural Weakness)
- **Evidence:** Verified by `test_atk_02_direct_service_invocation`.
- **Mitigation Strategy:** Secure the internal service methods or document that service object access requires pre-existing trust within the Python execution context.

### ATK-03 — Action Substitution
- **Threat:** A request authorized for action `A` (e.g., `status`) is manipulated in-flight to perform action `B` (e.g., `cancel`).
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_03_and_10_require_approval_must_not_execute_immediately` and `test_atk_04_05_payload_parameter_tampering`.
- **Mitigation Strategy:** Freeze the payload parameter structures inside the Orchestrator and evaluate action patterns deterministically.

### ATK-04 — Resource Substitution
- **Threat:** A request authorized for resource `A` is mutated to execute against resource `B` before capability invocation.
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_04_05_payload_parameter_tampering`.
- **Mitigation Strategy:** Bind the authorized resource ID securely to the request execution context and prevent post-authorization modification.

### ATK-05 — Parameter Tampering
- **Threat:** Dict payload contents inside a frozen `Request` are altered in-place after authorization check but before capability execution.
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_04_05_payload_parameter_tampering`.
- **Mitigation Strategy:** Perform a deep-freeze or dict-to-mapping proxy conversion in the Orchestrator to enforce actual immutability.

### ATK-06 — Capability Impersonation
- **Threat:** A malicious component replaces a legitimate capability in the `CapabilityRegistry`.
- **Pre-Remediation Status:** **BLOCKED**
- **Evidence:** Regression-tested by `test_registry_prevents_duplicate_capability_registration` in `test_s20_security.py`.
- **Mitigation Strategy:** Keep registry duplicate-check robust.

### ATK-07 — Privileged Capability Acquisition
- **Threat:** Unauthorized actors obtain direct capability references from the registry.
- **Pre-Remediation Status:** **VULNERABLE** (Architectural Weakness)
- **Evidence:** Verified by `test_atk_07_capability_reference_acquisition_from_registry`.
- **Mitigation Strategy:** Restrict registry lookup or accept capability possession as non-privileged while relying on execution-time context validation.

### ATK-08 — Confused Deputy (Step Execution Context Loss)
- **Threat:** Work execution steps call secondary capabilities, but fail to propagate the originating actor's identity context, causing failures or privilege escalations.
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_08_work_step_execution_context_loss_confused_deputy`.
- **Mitigation Strategy:** Propagate the authorizing actor identity through the Work lifecycle, planning steps, and down into `WorkService._invoke_capability`.

### ATK-09 — Authorization Context Loss
- **Threat:** Downstream capabilities cannot verify actor properties because the `AuthorizationDecision` is lost at the boundary.
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_09_capability_does_not_receive_authorization_decision`.
- **Mitigation Strategy:** Enrich the capability `Request` payload with structured, verified authorization context metadata before dispatch.

### ATK-10 — Authorization Result Manipulation (Approval Bypass)
- **Threat:** The policy returns `REQUIRE_APPROVAL` but the Orchestrator enriches the payload and continues to execute the sensitive action anyway.
- **Pre-Remediation Status:** **VULNERABLE**
- **Evidence:** Verified by `test_atk_03_and_10_require_approval_must_not_execute_immediately`.
- **Mitigation Strategy:** Halt execution in the Orchestrator if `REQUIRE_APPROVAL` is returned, preventing dispatch to the capability and returning a structured Response indicating pending approval status.

### ATK-11 — Failure / Exception Escape
- **Threat:** A failure during authorization or execution allows fall-through execution or privilege escalation.
- **Pre-Remediation Status:** **BLOCKED**
- **Evidence:** Verified by `test_atk_11_orchestrator_contains_capability_exceptions`.
- **Mitigation Strategy:** Retain fail-closed exception handling at the Orchestrator boundary.

### ATK-12 — Capability Composition
- **Threat:** Combined capabilities generate unauthorized privileges.
- **Pre-Remediation Status:** **POTENTIAL**
- **Mitigation Strategy:** Enforce least-privilege policies.

### ATK-13 — SYSTEM Capability Boundary Escape
- **Threat:** SYSTEM authority leaks from system-initiated operations to standard users.
- **Pre-Remediation Status:** **POTENTIAL**
- **Mitigation Strategy:** Validate actor boundaries during step execution.

### ATK-14 — Resource Ownership Confusion
- **Threat:** An authorized actor alters a resource they do not own.
- **Pre-Remediation Status:** **POTENTIAL**
- **Mitigation Strategy:** Enforce ownership constraints within the service layer.
