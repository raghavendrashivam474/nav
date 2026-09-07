# Sx1.F — Aggregate Hardening & Boundary Defense Analysis

**Sprint:** Sx1.F (Aggregate & Cross-Boundary Security Campaign)  
**Baseline:** `vx1.4`  

---

## 1. Hardening Baseline Preserved from Sx1.1–Sx1.4

Sx1.F verified that the cumulative hardening from previous security sprints functions cohesively under composition:

1. **Payload Isolation Snapshot (ATK-05 / Sx1.2):**
   `copy.deepcopy(request.payload)` is executed at the entry of `Orchestrator.route_request`. Any mutation of the caller's dictionary during or after dispatch does not affect security evaluation or capability execution.

2. **Strict Identity Sanitization (ATK-01/13 / Sx1.3):**
   - Untrusted dictionaries claiming `actor_type="system"` are stripped to `ActorType.USER`.
   - `SYSTEM_ACTOR` is strictly matched against the internal singleton instance.
   - Untrusted `trust_level` assertions are forced to `0`.
   - Actor metadata is frozen via `MappingProxyType` to prevent in-flight tampering.

3. **Deterministic Fail-Closed Authorization (S20 / Sx1.1):**
   - Policy evaluation precedes all capability dispatch.
   - Default outcome for unmapped actions or unknown actors is `DENY`.
   - `DENY` outcomes cannot be overridden by human approval.

4. **Context Propagation Across Nested Invocations (ATK-09 / Sx1.2 / Sx1.4):**
   - Verified `_security_actor` is injected by the Orchestrator into downstream capability requests.
   - `WorkService._invoke_capability` carries verified actor context into nested Orchestrator calls.

5. **Lifecycle State Machine Invariants (S17 / S18):**
   - Work items in terminal states (`CANCELLED`, `COMPLETED`, `FAILED`) reject all control actions.
   - Completed plan steps cannot be modified during plan revisions.
   - Retry limits (`max_retries`) are enforced on step execution.

---

## 2. Cross-Boundary Invariants Verified in Sx1.F

| Invariant | Enforced At | Validating Tests |
|---|---|---|
| **Actor Immutability** | `ActorIdentity.__post_init__` | `test_sxa_03`, `test_sxh_04` |
| **Authority Containment** | `Orchestrator.route_request` | `test_sxa_01`, `test_sxa_07`, `test_sxf_01` |
| **Separation of Privileges** | `PolicyEngine.evaluate` | `test_sxa_05`, `test_sxb_01`, `test_sxc_03` |
| **Approval Context Binding** | `Orchestrator` & `PolicyEngine` | `test_sxc_05`, `test_sxi_01` |
| **Nested Execution Isolation** | `NestedAttackerCapability` / `WorkService` | `test_sxe_01`, `test_sxe_03`, `test_sxj_02` |
| **Fail-Closed on Error** | `Orchestrator` exception handler | `test_sxj_04`, `test_sxf_05` |