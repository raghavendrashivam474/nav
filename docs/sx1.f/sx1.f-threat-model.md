# Sx1.F — Aggregate Threat Model: Cross-Boundary Attack Surfaces

**Sprint:** Sx1.F (Final Aggregate Campaign)  
**Baseline:** `vx1.4`  
**Threat Focus:** Compositional attacks where individual boundaries are hardened, but sequence, timing, nesting, persistence, or state reuse could allow privilege escalation.

---

## 1. Threat Actors & Capabilities

| Threat Actor | Capabilities | Objective |
|---|---|---|
| **Untrusted External Caller** | Injects arbitrary JSON dictionaries via API / Interaction Adapter. | Escalate from unauthenticated/anonymous to `SYSTEM` or privileged `USER`. |
| **Malicious Internal Agent** | Executes within capability layer; can issue nested requests to Orchestrator. | Execute unauthorized takeover, delete work, or escape capability sandbox. |
| **Local State Tamperer** | Modifies SQLite database rows directly or crafts malicious JSON state blobs. | Inject elevated permissions or alter workflow instructions on reload/resume. |
| **Replay Attacker** | Captures legitimate requests/approvals and replays them against different resources/actions. | Execute unauthorized destructive actions using previously granted tokens. |

---

## 2. Attack Vectors Evaluated Across Composed Boundaries
text

             [Ingress Tampering]
                      │
   ┌──────────────────┼──────────────────┐
   ▼                  ▼                  ▼
[Actor Spoofing] [Approval Replay] [State Injection]
(Campaign A) (Campaign C/I) (Campaign D/H)
│ │ │
└─────────► [Orchestrator] ◄──────────┘
│
[Nested Capability]
(Campaign E)
│
[Service Execution]
(Campaign B/J)
│
[Partial Failure]
(Campaign G)

text


### Vector 1: Identity & Authorization Composition (Campaigns A, B, F)
- **Threat:** Attacker provides an untrusted actor dictionary claiming elevated trust, or alters identity metadata between evaluation and dispatch.
- **Defense Mechanism:** Orchestrator deep-sanitizes actor representations, strips `SYSTEM` claims to `USER`, resets unverified `trust_level` to `0`, and freezes metadata dictionaries via `MappingProxyType`.

### Vector 2: Approval & Lifecycle Token Replay (Campaigns C, I)
- **Threat:** Pre-approval flag (`_security_approved`) granted for a harmless action is replayed or transferred to a sensitive action (e.g., `cancel`, `take_over`, `redirect`).
- **Defense Mechanism:** Policy evaluates each incoming `Request` deterministically. Approvals are contextual to the specific action and resource evaluated at dispatch time.

### Vector 3: Persistence Deserialization & Resume Injection (Campaigns D, H)
- **Threat:** Resuming persisted work from SQLite creates implicit authority or executes completed/terminal tasks.
- **Defense Mechanism:** Work lifecycle state machine strictly validates state transitions. Terminal work (`COMPLETED`, `CANCELLED`, `FAILED`) rejects all control and execution attempts.

### Vector 4: Nested Execution & Escalation via Re-entry (Campaigns E, J)
- **Threat:** A low-privilege capability makes nested calls back to Orchestrator to execute privileged actions.
- **Defense Mechanism:** Nested invocations re-enter Orchestrator dispatch and undergo full policy evaluation; caller actor context is forwarded and validated on each nesting level.

### Vector 5: Partial Failure & Dirty State Exploitation (Campaigns G, J)
- **Threat:** A step failure leaves behind reusable approval artifacts or corrupts retry counts.
- **Defense Mechanism:** Step retry limits are strictly enforced (`max_retries`), and failed execution logs the transition to `FAILED` without altering other steps.