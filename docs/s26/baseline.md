# S26 Baseline Audit — Comparison Foundation

**Sprint:** S26
**Baseline Tag:** `vx1.f` (Sx1 Blackbox Security Closure)
**Baseline Commit:** `5579082`
**Baseline Date:** March 2025

---

## 1. Baseline Test State

| Metric | Value |
|--------|-------|
| Tests Passed | 893 |
| Tests Skipped | 1 |
| Tests Deselected | 2 (live-network only) |
| Ruff Check | Clean (0 errors) |
| Working Tree | Clean |

The baseline is fully green. All Sx1 security invariants are intact.

---

## 2. Existing Pipeline (Before S26)

The NAV v2 intelligence pipeline ended at S25:

```text
S23 External Information
        ↓
S24 Evidence
        ↓
S25 Evidence Synthesis (produces Finding)
        ↓
[GAP — no capability for comparative evaluation]
3. Existing Assets S26 Builds On
3.1 Contracts (core/contracts/)
evidence.py: Evidence, EvidenceRelation, RelationType (SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM), EvaluationState, EvidenceTrace.
finding.py: Finding, FindingState (SUPPORTED, CONTESTED, INCONCLUSIVE, INSUFFICIENT_EVIDENCE).
capability.py: Capability (abstract with name, version, description, invoke), Request, Response.
ai.py: AIGateway, AIRequest, AIResponse (fields: content, model_used, usage, raw_response).
security.py: ActorIdentity, ActorType, AuthorizationOutcome, SYSTEM_ACTOR.
external_information.py: ExternalInformationItem (fields: content, source, relevance_hint), ExternalInformationResult (fields: status, items, provider_id, request_id), SourceMetadata, RetrievalStatus.
3.2 Capabilities (capabilities/)
capabilities/evidence/service.py: EvidenceService facade with ingest_result, evaluate, record_relation, trace, get_evidence, get_relations_for.
capabilities/evidence/store.py: In-memory EvidenceStore (no persistence layer per S24 §20).
capabilities/evidence/synthesis.py: Deterministic EvidenceSynthesizer producing Finding.
3.3 Orchestration & Security
core/orchestration/orchestrator.py: Enforces identity sanitization, deep payload snapshotting, SecurityService.authorize() gate, and _security_actor propagation.
core/capabilities/registry.py: CapabilityRegistry with register, get, list_capabilities.
4. Capability Gap Identified
S25 answers "What can this evidence collectively tell us?" but NAV cannot yet answer:

"How do these findings, evidence items, or alternatives relate, differ, agree, conflict, or compare?"

Comparison logic was previously trapped inside ad-hoc prompt templates. There was no first-class capability to represent structural comparative relationships with provenance and uncertainty preservation.

5. S26 Constraints Derived from Baseline
Additive Only: Existing S25 contracts (Finding, FindingState) must remain unchanged.
In-Memory Persistence: Follow S24 §20 — no new database.
Orchestrator Boundary: All access must flow through Orchestrator and honor SecurityService.
Sx1 Security Invariants: No bypass of actor sanitization, deep payload copy, or authorization gate.
No Fake Precision: No numerical trust scores or arbitrary weighting (per S24 §13 and S25 §14).
