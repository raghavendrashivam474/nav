# S27 Reasoning Capability — Implementation Details

**Sprint:** S27 — Reasoning
**Baseline:** `575efae` (NAV v2.3)
**Completed Date:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

---

## 1. Overview

S27 implements NAV's first-class **Reasoning capability**, bridging structural synthesis (S25) and comparative evaluation (S26) to a traceable, inspectable reasoning outcome. 

Rather than treating reasoning as an opaque LLM prompt, S27 establishes explicit, immutable contracts, separating **deterministic rule-based reasoning** from **model-assisted semantic reasoning**.

---

## 2. Component Design

### 2.1. Reasoning Contracts (`core/contracts/reasoning.py`)
- **`ReasoningInput`**: Wraps external inputs (Findings, Evidence, Comparisons, or arbitrary premises) with a unique identifier (`input_id`), typing, content, and optional links back to the original database entity (`source_id`).
- **`ReasoningStep`**: Represents an explicit logical inference step. Contains a sequential `step_number`, an `inference_type` enum (DEDUCTIVE, INDUCTIVE, ABDUCTIVE, COMPARATIVE, ELIMINATIVE, SYNTHETIC), a human-readable explanation, input premise references (`premise_ids`), and optional intermediate conclusions.
- **`ReasoningResult`**: An immutable snapshot of the reasoning process. Includes the target question, overall epistemological status (`ReasoningState` — SOUND, CONTESTED, INCONCLUSIVE, UNSUPPORTED, INSUFFICIENT_INPUTS), a tuple of inputs used, the sequential reasoning steps performed, the final conclusion, supporting/conflicting references, limitations, and full lineage tracing back to source findings, evidence items, and comparisons.

### 2.2. Reasoning Engine (`capabilities/reasoning/engine.py`)
- **`reason_over_findings`**: Deterministic rule-based reasoning. Propagates finding states (SUPPORTED, CONTESTED, INCONCLUSIVE) into syllogistic arguments. Contradictions from contested findings are propagated as explicit conflicts.
- **`reason_over_comparison`**: Deterministic rule-based reasoning over dimension evaluations. Analyzes comparative dominance (dimension-level favored options) and flags contradictions to yield clean sound or contested outcomes.
- **`reason_semantic`**: Model-assisted semantic reasoning. Packages untrusted inputs in XML boundary markers, prompts the AI Gateway with strict JSON schemas, validates structural constraints (no type mismatching or invalid states), and sanitizes any hallucinated references (scrubbing premise IDs that were not supplied to the engine).
- **`fallback`**: Reliable deterministic fallback when the AI Gateway is absent or raises runtime exceptions.

### 2.3. Reasoning Service (`capabilities/reasoning/service.py`)
Provides high-level coordinator methods bridging `EvidenceService` and `ComparisonService` to the `ReasoningEngine`.

### 2.4. Reasoning Capability (`capabilities/reasoning/capability.py`)
Exposes Orchestrator-facing actions:
- `reason_over_findings`
- `reason_over_comparison`
- `reason`

Handles payload validation, dictionary parsing, fail-closed error propagation, and security boundaries.

---

## 3. Testing and Security

- **Contract Tests**: Verified immutability (`@dataclass(frozen=True)`), serialization, invalid-state construction, and schema properties.
- **Deterministic Evaluation**: Verified syllogistic rules, support asymmetries, contradiction propagation, and comparative dominance.
- **Model Isolation**: Evaluated strict XML tagging of untrusted premises, schema parsing, and sanitization of hallucinated identifiers.
- **Adversarial Testing**: Tested prompt injection resistance, deeply nested malformed JSON, massive finding arrays (100 items), and malformed payloads.
