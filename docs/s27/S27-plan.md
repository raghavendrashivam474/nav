# S27 Implementation Plan: Reasoning Subsystem

**Sprint:** S27 — Reasoning
**Status:** In Progress
**Baseline:** `575efae` (NAV v2.3)

---

## 1. Objective

Deliver NAV's first-class **Reasoning capability**, bridging:
`Acquire (S23) → Represent (S24) → Synthesize (S25) → Compare (S26) → REASON (S27) → Decide (S28) → Act (S29)`

The capability will:
1. Take structured inputs (`Finding`, `Evidence`, `ComparisonResult`, raw propositions).
2. Produce structured, inspectable, and traceable `ReasoningResult` artifacts with explicit reasoning steps, intermediate conclusions, conflict flags, and final conclusion.
3. Support both deterministic rule-based inference and model-assisted semantic reasoning with strict schema enforcement, hallucination sanitization, and fallback behavior.
4. Integrate with the Capability interface and Orchestrator.

---

## 2. Architecture & Deliverables

### Phase 1: Contracts (`core/contracts/reasoning.py`)
- `ReasoningInputType` (Enum)
- `InferenceType` (Enum)
- `ReasoningState` (Enum)
- `ReasoningInput` (Frozen Dataclass)
- `ReasoningStep` (Frozen Dataclass)
- `ReasoningResult` (Frozen Dataclass)
- Re-export in `core/contracts/__init__.py`

### Phase 2: Engine (`capabilities/reasoning/engine.py`)
- `ReasoningEngine`
  - Deterministic reasoning over findings:
    - Support aggregation, contradiction propagation, syllogistic chain building.
  - Deterministic reasoning over comparisons:
    - Comparative dominance derivation, trade-off synthesis.
  - Model-assisted reasoning for complex/heterogeneous inputs:
    - XML-fenced prompt boundaries (`<untrusted_inputs>`, `<query>`).
    - JSON schema validation.
    - Sanitization of hallucinated premise IDs / input references.
    - Deterministic fallback when gateway is unavailable or fails.

### Phase 3: Service (`capabilities/reasoning/service.py`)
- `ReasoningService`
  - Coordinator integrating `EvidenceService`, `ComparisonService`, and `ReasoningEngine`.
  - Methods:
    - `reason_over_findings(query, findings)`
    - `reason_over_comparison(query, comparison)`
    - `reason(query, inputs)`

### Phase 4: Capability Integration (`capabilities/reasoning/capability.py`)
- `ReasoningCapability`
  - Subclasses `core.contracts.capability.Capability`.
  - Actions:
    - `reason_over_findings`
    - `reason_over_comparison`
    - `reason`
  - Re-export in `capabilities/__init__.py`.

### Phase 5: Test Suite
- `tests/test_s27_reasoning.py`:
  - Contract validation, immutability, serialization.
  - Deterministic reasoning tests (support, conflict, multi-step chains, comparisons).
  - Model-assisted tests with mock AI gateways.
  - Service and Capability invocation tests.
- `tests/test_s27_adversarial.py`:
  - Hallucinated input references, cyclic dependencies, malformed model payloads, prompt injection resilience, empty/extreme inputs, security boundary checks.

### Phase 6: Documentation & Completion
- `docs/s27/implementation.md`
- `docs/s27/completion-report.md`
- `docs/s27/post-completion-report.md`
- `docs/architecture/decisions/0017-s27-reasoning-capability.md`
- Final regression verification (all 913+ tests).

---

## 3. Boundary & Non-Goals

- **NO Decision Making:** S27 does NOT decide "choose X" or "execute action Y". That is S28.
- **NO Autonomous Loops:** S27 does not execute actions or loop autonomously. That is S29.
- **NO New Persistence Store:** S27 produces transient, returnable immutable objects; persistence is not mandated.
- **NO Hidden Chain-of-Thought:** S27 records explicit, structured step summaries, not uninspected model scratchpads.
