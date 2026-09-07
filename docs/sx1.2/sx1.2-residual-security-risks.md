# Sx1.2 — Residual Security Risks

**Project:** Aryntra Blackbox
**Security Sprint:** Sx1.2 — Capability & Execution Boundary
**Status:** Open-risk register / future attack surface
**Scope:** Capability invocation, execution boundaries, service direct access, parameter immutability

---

## 1. Baseline Summary

Sx1.2 investigated the capability and execution boundaries following the S20 authorization decision. 

The campaign demonstrated and resolved three critical vulnerabilities:
1. **REQUIRE_APPROVAL Execution Escape (FIXED):** Orchestrator halted dispatch on `REQUIRE_APPROVAL` unless explicitly accompanied by verified human confirmation (`_security_approved`).
2. **Post-Authorization Parameter Tampering (FIXED):** Orchestrator performs defensive deep snapshots to guarantee that authorized parameters match executing parameters.
3. **Work Step Context Loss / Confused Deputy (FIXED):** Initiating actor identity is persisted in Work metadata and propagated to step execution requests.

---

## 2. Residual Risk Register

| ID | Risk / Attack Surface | Classification | Severity | Follow-up |
|---|---|---|---|---|
| **RR-01** | Direct `WorkService` invocation bypassing Orchestrator | **BLOCKED (Internal Trust)** | Low (In-Process) | Architecture Boundary |
| **RR-02** | Identity provenance / cryptographic token assertion | **OPEN** | High* | Future IAM / Auth |
| **RR-03** | Capability registration tampering / monkey patching | **BLOCKED** | Low (Protected) | Runtime Integrity |
| **RR-04** | Direct capability reference invocation from registry | **BLOCKED (Internal Trust)** | Low (In-Process) | Capability Policy |
| **RR-05** | Distributed / Multi-device authority propagation | **FUTURE** | High* | Distributed Nav |
| **RR-06** | Complex capability composition side effects | **POTENTIAL** | Medium | Asynchronous Work |
| **RR-07** | Step payload schema injection | **POTENTIAL** | Medium | Work Planner |

* Severity reflects risk if boundaries become exposed over remote network transport.
