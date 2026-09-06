# S23 Reconnaissance Notes

> **STATUS:** COMPLETE
> **Sprint:** S23 — External Information Capability
> **Rule:** Do NOT implement before answering all questions below.

---

## A. Where does research currently enter NAV?

**Finding:**
Research inputs enter the system through the orchestrator's capability router. Specifically, when the orchestrator parses an intention requiring external context, it prepares a request packet and queries the registry for the target capability.

---

## B. What capability currently represents research/investigation?

**Finding:**
The existing baseline capability is structured inside `capabilities/research/` as `ResearchCapability`. In v1, this was a mock-bound layer that simulated retrieval. In S23, we established the clean capability boundary interface to decouple this mock layer from real data fetching.

---

## C. What is the capability invocation boundary?

**Finding:**
The boundary is governed by standard execution signatures:
`execute(self, request: CapabilityRequest, context: NavContext) -> CapabilityResponse`.

---

## D. How are capability requests represented?

**Finding:**
Capability requests inherit from base contracts inside `core/contracts/`. They utilize structured Python dataclasses with frozen/read-only fields, standardizing fields like `request_id`, `actor_id`, and payload properties.

---

## E. How does the Orchestrator dispatch them?

**Finding:**
`core/orchestration/orchestrator.py` resolves a request by:
1. Matching the request type to its mapped registration.
2. Routing it through the security manager for execution privileges.
3. Invoking the target capability's execute function.
4. Handling response codes and returning execution control.

---

## F. Where does S20 authorization happen?

**Finding:**
S20 authorization happens entirely within `core/security/` inside the `SecurityPlane` or `AccessController` before capability invocation. The orchestrator explicitly verifies actor permissions prior to routing to avoid unprivileged capability execution.

---

## G. How is actor/request context propagated?

**Finding:**
Context is maintained via `NavContext` (defined in `core/context/`), which encapsulates active runtime states, execution trace scopes, and security identities, passing alongside standard requests throughout the execution sequence.

---

## H. Is there already an external-information abstraction?

**Finding:**
No. Prior to S23, no formal external information abstraction existed. Any simulated search logic was directly coupled to mock methods inside research-level tests, reinforcing the urgency of this sprint.

---

## I. What existing contracts can S23 reuse?

**Contracts to reuse:**
- `core.contracts.CapabilityRequest` (adapted structurally)
- `core.contracts.CapabilityResponse` (adapted structurally)
- `core.context.NavContext` (for trace/request correlation)

---

## J. What is the smallest insertion point?

**Smallest insertion point:**
The most isolated and safest insertion point is establishing `core/contracts/external_information.py` to house the exchange structures, alongside a dedicated capability module under `capabilities/external_information/` representing the provider registry boundary.

---

## Architectural Decision

- [x] **Case A:** Existing architecture is sufficient — additive only
- [ ] **Case B:** Small contract extension needed — document below
- [ ] **Case C:** Existing architecture prevents capability — ADR required

**Decision:**
Case A. The existing security and orchestration planes cleanly map capability payloads. No system refactoring is needed; we are implementing a standard additive capability boundary.

---

## Recon Complete

- [x] All questions answered
- [x] Decision made
- [x] Ready to proceed to implementation
