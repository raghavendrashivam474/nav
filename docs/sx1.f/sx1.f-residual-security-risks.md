# Sx1.F — Residual Security Risks & Operational Boundaries

**Sprint:** Sx1.F (Aggregate & Cross-Boundary Security Campaign)  
**Baseline:** `vx1.4`  

---

## 1. Overview of Residual Risks

Sx1.F completed aggregate testing across all combined security boundaries of NAV. All critical execution invariants held across composite attack chains.

The residual risks identified are **inherent to NAV's current local in-process runtime model** and do not represent exploitable vulnerabilities in the present deployment:

---

## 2. Risk Ledger

### RISK-01: Direct Internal Python Method Invocation
* **Description:** Any internal Python code holding a direct reference to `WorkService`, `PolicyEngine`, or `SQLiteWorkRepository` can invoke methods without passing through `Orchestrator.route_request()`.
* **Current Boundary:** In the current single-process architecture, external requests exclusively enter via interaction adapters that route through the `Orchestrator`. Direct service references are not exposed across external interfaces.
* **Residual Impact:** Low. Relevant only if untrusted 3rd-party plugins are loaded into the same Python interpreter.
* **Mitigation for Future Sprints:** Dynamic capability sandboxing or RPC-separated capability workers.

---

### RISK-02: Absence of Cryptographic HMAC on SQLite Database Records
* **Description:** Persisted Work items and JSON blobs in SQLite are not cryptographically signed.
* **Current Boundary:** Access to the SQLite database file requires local filesystem read/write privileges on the host machine.
* **Residual Impact:** Low. An attacker with host filesystem access already has process-level control.
* **Mitigation for Future Sprints:** Envelope encryption and HMAC signing for persisted state blobs when transitioning to shared/distributed storage.

---

### RISK-03: In-Memory Security Event Log Eviction
* **Description:** `SecurityEventLog` retains the most recent 10,000 events in memory and discards older events upon reaching capacity.
* **Current Boundary:** Security events are used for observability and debugging, not compliance audit log durability.
* **Residual Impact:** Low.
* **Mitigation for Future Sprints:** Structured append-only persistent logging backend (e.g. SQLite/syslog audit sink).

---

### RISK-04: Approval Mechanism Relies on Contextual Payload Flag
* **Description:** Human approval is indicated by `_security_approved: True` evaluated in context by the Orchestrator, rather than a standalone cryptographic token.
* **Current Boundary:** The Orchestrator strictly evaluates authorization policy on every request and isolates payloads, preventing flag leakage or privilege escalation across actions/resources.
* **Residual Impact:** Low in single-process runtime.
* **Mitigation for Future Sprints:** Cryptographic approval capability tokens for distributed/asynchronous approvals.