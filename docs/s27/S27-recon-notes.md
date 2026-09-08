# S27 Reconnaissance Notes: Reasoning Architecture

**Sprint:** S27 — Reasoning Capability
**Status:** Completed Reconnaissance
**Baseline:** `575efae` (NAV v2.3)

---

## 1. Reconnaissance Questions & Answers

### Q1: What existing contracts can S27 consume?
- `core.contracts.finding.Finding` and `FindingState` (S25)
- `core.contracts.evidence.Evidence`, `EvidenceRelation`, and `RelationType` (S24)
- `core.contracts.comparison.ComparisonResult`, `ComparisonSubject`, `ComparisonDimension`, `ComparisonRelationship`, and `ComparisonState` (S26)
- `core.contracts.ai.AIGateway`, `AIRequest`, `AIMessage`, `AIResponse` (Core AI layer)
- `core.contracts.capability.Capability`, `Request`, `Response` (Capability interface)

### Q2: What existing services can S27 reuse?
- `capabilities.evidence.service.EvidenceService` (to resolve evidence items, relations, provenance traces)
- `capabilities.comparison.service.ComparisonService` (to invoke comparative evaluations if needed)

### Q3: How does S26 represent comparisons?
- `ComparisonResult` contains:
  - `subjects`: tuple of `ComparisonSubject`
  - `dimensions`: tuple of `ComparisonDimension`
  - `evaluations`: tuple of `DimensionEvaluation` (each with `relationship`, `favored_subject_id`, `supporting_evidence_ids`, `supporting_finding_ids`)
  - `state`: `ComparisonState` (CONCLUSIVE, CONTESTED, INCONCLUSIVE, INSUFFICIENT_DATA, INCOMPARABLE)
  - `finding_basis`, `evidence_basis`: provenance tuples

### Q4: How does S25 represent findings?
- `Finding` contains:
  - `claim`: str
  - `status`: `FindingState` (SUPPORTED, CONTESTED, INCONCLUSIVE, INSUFFICIENT_EVIDENCE)
  - `supporting_evidence`: tuple[str, ...]
  - `contradicting_evidence`: tuple[str, ...]
  - `evidence_basis`: tuple[str, ...]
  - `uncertainty`: str
  - `synthesis_basis`: str

### Q5: How are AI/model calls currently isolated?
- AI Gateway contract: `AIGateway.generate(AIRequest) -> AIResponse`.
- Untrusted input boundary: All model inputs are wrapped in explicit boundary tags (e.g. `<untrusted_subjects>`, `<untrusted_evidence>`).
- Structured response enforcement: Strict JSON schemas requested; JSON parser validates keys and types.
- Fallback & Sanitization: Hallucinated references are scrubbed; deterministic fallback occurs if AI gateway is absent or raises exceptions.
- Model is never authority: Model responses are analytical data subject to validation.

### Q6: What existing capability conventions must S27 follow?
- Directory layout: `capabilities/reasoning/` (`__init__.py`, `capability.py`, `engine.py`, `service.py`).
- Subclasses `Capability` implementing `name`, `version`, `description`, and `invoke(Request) -> Response`.
- Action routing with payload validation and descriptive error handling.
- Re-exports in `core/contracts/__init__.py` and top-level `capabilities/__init__.py`.

### Q7: What existing security boundaries affect S27?
- Sx1 capability invocation boundaries and fail-closed payload validation.
- Model untrusted content isolation (S8/Sx1.3).
- Prohibition against inventing authoritative NAV entities (ghost evidence/findings).

### Q8: What is the smallest architecture that can implement S27?
- **Contracts (`core/contracts/reasoning.py`):**
  - `InferenceType` (DEDUCTIVE, INDUCTIVE, ABDUCTIVE, COMPARATIVE, ELIMINATIVE)
  - `ReasoningState` (SOUND, CONTESTED, INCONCLUSIVE, UNSUPPORTED, INSUFFICIENT_INPUTS)
  - `ReasoningInput` (polymorphic container for finding, evidence, comparison, or premise references)
  - `ReasoningStep` (step_index, inference_type, explanation, premise_ids, intermediate_conclusion, confidence_indicator)
  - `ReasoningResult` (reasoning_id, question_or_goal, state, inputs, steps, final_conclusion, supporting_references, conflicting_references, limitations, metadata)
- **Engine (`capabilities/reasoning/engine.py`):**
  - Deterministic reasoning over findings & comparisons (syllogistic deduction, contradiction propagation, comparative dominance)
  - Model-assisted reasoning over complex semantic claims with strict sanitization and fallback
- **Service (`capabilities/reasoning/service.py`):**
  - High-level coordinator linking EvidenceService, ComparisonService, and ReasoningEngine
- **Capability (`capabilities/reasoning/capability.py`):**
  - Orchestrator entry point exposing actions: `reason_over_findings`, `reason_over_comparison`, `reason_hybrid`

### Q9: Are any architectural gaps actually blocking S27?
- **None.** All prerequisite contracts (S24, S25, S26, AI Gateway, Capability) are in place and verified healthy.
