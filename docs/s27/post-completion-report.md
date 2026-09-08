---

# S27 Reasoning Capability — Post-Implementation Report

**To:** Senior Development Lead
**From:** S27 Implementation
**Date:** 2025-07-11
**Sprint:** S27 — Reasoning
**Baseline:** NAV v2.3 / `575efae`
**Security Baseline:** Sx1.F — CLOSED (untouched)
**Status:** ✅ COMPLETE — All Definition-of-Done criteria met

---

## 1. Executive Summary

S27 introduces NAV's first durable **Reasoning primitive**. Prior to this sprint, NAV could acquire information (S23), evaluate evidence (S24), synthesize findings (S25), and compare subjects (S26) — but it had no structured mechanism to explain *how* a set of findings and comparisons leads to a conclusion.

S27 closes that gap. The system now produces explicit, inspectable, and fully traceable reasoning chains that map inputs → inference steps → intermediate conclusions → final conclusion, with honest representation of conflicts and limitations.

**This is not a smarter prompt.** It is an architectural primitive that future capabilities (S28 Decision, S29 Action) will consume.

---

## 2. What Was Built

### 2.1 Reasoning Contracts (`core/contracts/reasoning.py`)

Three frozen, immutable dataclasses and three enums:

| Contract | Purpose |
|---|---|
| `ReasoningInputType` | Classifies inputs: FINDING, EVIDENCE, COMPARISON, PREMISE, OBSERVATION |
| `InferenceType` | Classifies logic mode: DEDUCTIVE, INDUCTIVE, ABDUCTIVE, COMPARATIVE, ELIMINATIVE, SYNTHETIC |
| `ReasoningState` | Epistemological status: SOUND, CONTESTED, INCONCLUSIVE, UNSUPPORTED, INSUFFICIENT_INPUTS |
| `ReasoningInput` | Wraps a discrete knowledge unit with `input_id`, `content`, `input_type`, and optional `source_id` back to the originating entity |
| `ReasoningStep` | One explicit inference: `step_number`, `inference_type`, `description`, `premise_ids` (referencing `ReasoningInput.input_id`), `intermediate_conclusion`, `confidence_assessment` |
| `ReasoningResult` | Full reasoning artifact: `question`, `state`, `inputs`, `steps`, `final_conclusion`, `supporting_input_ids`, `conflicting_input_ids`, `limitations`, plus provenance tuples (`finding_basis`, `evidence_basis`, `comparison_basis`) |

All contracts are model- and provider-independent. No LLM-specific structures, no internal chain-of-thought dumps, no OpenAI response shapes.

### 2.2 Reasoning Engine (`capabilities/reasoning/engine.py`)

Three reasoning paths:

**Path A — Deterministic Finding Reasoning (`reason_over_findings`)**
Consumes S25 `Finding` objects. Classifies by `FindingState` (SUPPORTED / CONTESTED / INCONCLUSIVE / INSUFFICIENT_EVIDENCE). Propagates support asymmetries and contradictions into explicit reasoning steps. Zero LLM calls. Fully deterministic — same inputs always produce the same output.

**Path B — Deterministic Comparison Reasoning (`reason_over_comparison`)**
Consumes S26 `ComparisonResult` objects. Evaluates comparative dominance across dimension evaluations. Detects contradictory relationships. Derives reasoning state from the comparison's own `ComparisonState`. Zero LLM calls.

**Path C — Model-Assisted Semantic Reasoning (`reason_semantic`)**
For heterogeneous or unstructured inputs where deterministic rules are insufficient. Uses the existing `AIGateway` abstraction with:
- XML-fenced untrusted input boundaries (`<untrusted_inputs>`, `<question>`)
- Strict JSON schema enforcement on model output
- Reference sanitization: any premise ID returned by the model that was not in the original input set is silently scrubbed
- State validation: invalid `ReasoningState` values trigger fallback
- Graceful deterministic fallback when the gateway is absent, raises exceptions, or returns malformed payloads

The model is treated as **untrusted analytical input**, never as authority.

### 2.3 Reasoning Service (`capabilities/reasoning/service.py`)

Facade coordinating `EvidenceService`, `ComparisonService`, and `ReasoningEngine`. Three methods mirror the engine's three paths. This is the integration point S28 will consume.

### 2.4 Reasoning Capability (`capabilities/reasoning/capability.py`)

Orchestrator-facing `Capability` subclass. Three actions:
- `reason_over_findings` — payload: `{question, findings[]}`
- `reason_over_comparison` — payload: `{question, comparison{}}`
- `reason` — payload: `{question, inputs[]}`

Full payload validation, dict-to-contract parsing, fail-closed error handling. Follows the exact pattern established by S26's `ComparisonCapability`.

---

## 3. Architecture Decisions

### 3.1 Deterministic-First
The majority of S27 reasoning is deterministic. Model assistance is used only when the input structure genuinely requires semantic interpretation. This keeps reasoning fast, repeatable, and auditable.

### 3.2 No New Persistence
S27 produces transient, immutable `ReasoningResult` objects. No new database, no reasoning history store. This follows the S26 precedent. Persistence is a separate concern for a future sprint if needed.

### 3.3 No Decision or Action
S27 deliberately stops at "here is what the evidence supports and what conflicts remain." It does not answer "which option should the user choose" (S28) or execute anything (S29). The `ReasoningResult.final_conclusion` is a structured justification, not a directive.

### 3.4 No Hidden Chain-of-Thought
S27 records explicit `ReasoningStep` summaries suitable for system and user inspection. It does not persist raw model scratchpads or internal chain-of-thought traces.

### 3.5 Contract Ownership
The reasoning contract belongs to NAV, not to any model provider. The `AIGateway` is one replaceable implementation mechanism inside the engine. Swapping models or providers requires zero contract changes.

---

## 4. Integration with Existing Architecture

| Existing Component | S27 Relationship |
|---|---|
| `core.contracts.finding.Finding` | Consumed as `ReasoningInput` with `input_type=FINDING` |
| `core.contracts.evidence.Evidence` | Consumed as `ReasoningInput` with `input_type=EVIDENCE` |
| `core.contracts.comparison.ComparisonResult` | Consumed directly by `reason_over_comparison` |
| `core.contracts.ai.AIGateway` | Used by `reason_semantic`; unchanged |
| `core.contracts.capability.Capability` | Subclassed by `ReasoningCapability`; unchanged |
| `capabilities.evidence.service.EvidenceService` | Injected into `ReasoningService` for evidence resolution |
| `capabilities.comparison.service.ComparisonService` | Injected into `ReasoningService` for comparison resolution |
| `core.contracts.__init__.py` | Updated to re-export S27 contracts (only existing file modified) |

**No existing contracts were modified.** No S23–S26 code was changed. The only mutation to an existing file was adding re-exports to `core/contracts/__init__.py`.

---

## 5. Security Posture

S27 operates entirely within the existing Sx1 security boundary. No new security mechanisms were introduced.

| Threat | Mitigation |
|---|---|
| Prompt injection via input content | All inputs wrapped in `<untrusted_inputs>` XML fences; model instructed to treat content as untrusted analytical material |
| Hallucinated reference IDs | `_sanitize_id_list()` cross-references all model-returned IDs against the known input set; unknown IDs are silently dropped |
| Malformed model output | JSON parsing with fallback; state enum validation; step structure validation; type checking on all fields |
| Model unavailability | Deterministic fallback produces an honest `INCONCLUSIVE` result with `reasoning_source: "fallback"` metadata |
| Ghost entities | Model cannot invent authoritative NAV entities; all references are validated against supplied inputs |
| Capability boundary crossing | `ReasoningCapability` validates all payloads before dispatch; malformed payloads return explicit errors without side effects |

---

## 6. Test Coverage

### 6.1 Test Suite Summary

| Suite | Tests | Coverage |
|---|---|---|
| `tests/test_s27_reasoning.py` | 43 | Contracts, immutability, deterministic reasoning (findings + comparisons), model-assisted reasoning (valid/invalid/fallback), service methods, capability invocation |
| `tests/test_s27_adversarial.py` | 6 | Prompt injection, total hallucination, type-mismatched JSON, massive payloads (100 findings), malformed action payloads, non-dict input elements |
| **Total S27** | **49** | |

### 6.2 Regression Results

| Metric | Pre-S27 | Post-S27 | Delta |
|---|---|---|---|
| Tests passed | 913 | 962 | +49 |
| Tests skipped | 1 | 1 | 0 |
| Tests deselected | 2 | 2 | 0 |
| Tests failed | 0 | 0 | 0 |
| Ruff errors | 0 | 0 | 0 |
| Mypy errors (S27) | N/A | 0 | — |
| Mypy errors (pre-existing) | 14 | 14 | 0 |

The 14 pre-existing mypy errors in Sx1/S26/S23 test files were present in the frozen baseline and were not touched per the backward compatibility rule.

---

## 7. Files Changed

### New Files (9)
```
core/contracts/reasoning.py
capabilities/reasoning/__init__.py
capabilities/reasoning/engine.py
capabilities/reasoning/service.py
capabilities/reasoning/capability.py
tests/test_s27_reasoning.py
tests/test_s27_adversarial.py
docs/s27/baseline.md
docs/s27/S27-recon-notes.md
docs/s27/S27-plan.md
docs/s27/implementation.md
docs/s27/completion-report.md
docs/s27/post-completion-report.md
docs/architecture/decisions/0017-s27-reasoning-capability.md
```

### Modified Files (1)
```
core/contracts/__init__.py  (added S27 re-exports only)
```

---

## 8. Known Limitations & Deferred Items

| Item | Status | Rationale |
|---|---|---|
| Persistent reasoning history | Deferred | No demonstrated need; follows S26 no-persistence precedent |
| Numerical confidence scores | Excluded | Brief explicitly prohibits fake precision; qualitative `confidence_assessment` used instead |
| Multi-turn reasoning / agent loops | Out of scope | Belongs to a future capability beyond S29 |
| Reasoning over S23 sources directly | Not implemented | S27 consumes S24/S25/S26 outputs; S23 data flows through those layers first |
| Confidence calibration | Deferred | Would require empirical validation data not currently available |

---

## 9. Readiness for S28 (Decision)

S27 is architecturally ready to feed S28. The `ReasoningResult` contract provides:
- A clear `state` field indicating whether the reasoning is SOUND, CONTESTED, or INCONCLUSIVE
- Explicit `supporting_input_ids` and `conflicting_input_ids` for trade-off analysis
- A `final_conclusion` that S28 can evaluate as a decision input
- Full provenance tuples for audit trails

S28 can consume `ReasoningResult` objects without any S27 modifications.

---

## 10. Verification Steps

To independently verify this implementation:

```bash
git checkout 575efae   # or the S27 release tag once created
pytest -v              # expect 962 passed, 1 skipped, 2 deselected
ruff check core capabilities tests   # expect 0 errors
mypy core/contracts/reasoning.py capabilities/reasoning/   # expect 0 errors
```

---

## 11. Conclusion

S27 delivers exactly what the brief specified: a durable, explicit, inspectable reasoning primitive that consumes NAV's existing structured knowledge representations and produces traceable conclusions. It does not make decisions, does not execute actions, does not introduce new security surfaces, and does not modify any completed capability.

The system can now answer the question: *"Given what we know, what relationships and reasoning steps connect the available evidence to a conclusion?"* — with full structural transparency.

**S27 is complete and ready for review.**

---

*End of report.*