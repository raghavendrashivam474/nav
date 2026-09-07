# Sx1.F — Speculative & Future Attack Vectors

**Sprint:** Sx1.F (Aggregate & Cross-Boundary Security Campaign)  
**Context:** Prospective threats relevant to future distributed, multi-user, multi-device, or plugin-enabled NAV architectures.

---

## 1. Future Distributed Architecture Threats
[Remote User Device] ──(Network)──► [Gateway / Auth Router] ──(RPC)──► [NAV Core]
│
┌───────────────────────────┴───────────────────────────┐
▼ ▼
[External Plugin Worker] [Asynchronous Actuator]

text


---

## 2. Speculative Attack Scenarios

### SPEC-01: Asynchronous Work Execution Race Window
* **Threat:** When NAV introduces asynchronous multi-threaded workers for long-running tasks, an attacker might submit a plan revision while a step is actively executing.
* **Countermeasure Design:** Implement atomic transactional state transitions with optimistic concurrency version checking (`plan.version`) at the repository level.

---

### SPEC-02: External Plugin Capability Sandbox Escape
* **Threat:** 3rd-party capability plugins loaded into the runtime could inspect process memory to locate `SYSTEM_ACTOR` singleton or tamper with `CapabilityRegistry`.
* **Countermeasure Design:** Execute untrusted capabilities in isolated subprocesses or containerized micro-vms with gRPC/IPC communication boundaries.

---

### SPEC-03: Distributed Replay of Human Approval Grants
* **Threat:** In a multi-device setup, an approval granted on a mobile interface could be intercepted on the wire and replayed to authorize a distinct sensitive action.
* **Countermeasure Design:** Issue short-lived, single-use, cryptographically signed approval tokens bound to `(action, resource, payload_hash, timestamp, nonce)`.

---

### SPEC-04: Multi-Tenant Workspace Boundary Pollution
* **Threat:** In a multi-user deployment, User A might query or manipulate Work items created by User B if tenancy checks are only performed at the interaction layer.
* **Countermeasure Design:** Enforce tenant/workspace isolation as a mandatory parameter in `PolicyEngine.evaluate()` and repository query filters.