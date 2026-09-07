# Sx1.F — Reconnaissance: Aggregate Architecture & Trust Boundary Map

**Sprint:** Sx1.F (Aggregate & Cross-Boundary Security Campaign)  
**Baseline:** `vx1.4`  
**Scope:** Full-lifecycle composition of Identity, Authorization, Approval, Capability Dispatch, Work Management, Persistence, Nested Execution, and Recovery.

---

## 1. System Execution & Trust Flow

The logical security path through NAV connects six distinct subsystems:
[Untrusted External Input]
│
▼
[Interaction Adapter / API Boundary]
│ (dict / raw Request)
▼
[Orchestrator Boundary]
├── 1. Payload Deepcopy Snapshot (ATK-05 parameter tampering mitigation)
├── 2. Actor Sanitization (dict / forged SYSTEM -> demoted to USER, trust_level=0)
├── 3. Deterministic Policy Evaluation (SecurityService -> PolicyEngine)
├── 4. Approval Gate Enforcement (_security_approved boolean check)
└── 5. Context Injection (_security_actor stamped into payload)
│
▼
[Capability Registry & Dispatch]
│ (Request with _security_actor)
▼
[WorkCapability & WorkService]
├── 6. Action Routing (_handle_create, _handle_cancel, etc.)
├── 7. Work Lifecycle & Step State Machine (PENDING -> READY -> RUNNING -> COMPLETED)
├── 8. Nested Execution (_invoke_capability -> Orchestrator.route_request)
└── 9. Plan Revision Integrity Guards (immutable step verification)
│
▼
[Persistence Layer: SQLiteWorkRepository]
├── 10. JSON Serialization (_work_to_data_blob)
└── 11. Row Deserialization & Hydration (_data_blob_to_fields, _row_to_work)

text


---

## 2. Boundary Transitions & State Handoffs

| Stage | Entry Boundary | Handoff Artifact | Invariant Enforced |
|---|---|---|---|
| **1. Ingress** | External → Interaction Layer | Raw `Request` dictionary | Deepcopy snapshot prevents post-auth payload mutation. |
| **2. Identity** | Interaction → Orchestrator | `_actor` payload field | Untrusted input cannot claim `SYSTEM` or nonzero `trust_level`. Metadata is frozen (`MappingProxyType`). |
| **3. Authorization** | Orchestrator → SecurityService | `AuthorizationRequest` | Deterministic policy evaluation; first matching rule wins; default DENY. |
| **4. Approval** | Policy Engine → Orchestrator | `AuthorizationDecision` | `REQUIRE_APPROVAL` halts dispatch unless `_security_approved=True`. DENY cannot be overridden by approval. |
| **5. Dispatch** | Orchestrator → CapabilityRegistry | `Request` with `_security_actor` | Capability receives validated identity context. |
| **6. Execution** | Capability → WorkService | Step inputs / lifecycle calls | Step state machine prevents illegal status transitions (e.g. terminal work execution). |
| **7. Persistence** | WorkService → SQLiteWorkRepository | `Work` dataclass → DB Row | Metadata preserves `initiating_actor` provenance across restarts. |
| **8. Re-entry** | WorkService → Orchestrator | Nested `Request` | Nested capability calls re-evaluate policy with forwarded actor context. |

---

## 3. Threat Surfaces Under Composition

Sx1.F systematically probed interactions where individual boundary guarantees could break down when composed:

1. **Identity ↔ Authorization:** Can an actor validly authorized for Action A reuse its authenticated token/context to execute Action B?
2. **Approval ↔ Capability:** Can an approval flag be replayed across different work IDs, actions, or modified payloads?
3. **Persistence ↔ Execution:** Can resuming persisted work bypass initial authorization checks or mutate step definitions?
4. **Nested Re-entry ↔ Authority Escalation:** Can a low-privilege capability trigger a nested privileged action through the orchestrator?
5. **Partial Failure ↔ State Divergence:** Can a step failure leave behind reusable authorization state or corrupt work item integrity?