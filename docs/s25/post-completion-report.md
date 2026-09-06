---

# NAV v2 — Sprint S25 Post-Completion Report

**To:** Senior Reviewer
**From:** Junior Developer
**Date:** 2026-09-06
**Sprint:** S25 — Evidence Synthesis, Conflict Resolution & Reasoned Findings
**Version:** NAV v2.1 → v2.2
**Starting Commit:** `b51366e` (tag `v2.1`)
**Branch:** `feature/s25-evidence-synthesis`
**Architecture Classification:** Case A — Purely Additive

---

## 1. Executive Summary

Sprint S25 successfully delivered a deterministic evidence synthesis capability for NAV v2. The system can now accept a bounded set of S24 Evidence items, inspect their explicit structural relationships, and produce a structured `Finding` that honestly represents support, contradiction, uncertainty, and full provenance — without manufacturing certainty the evidence does not justify.

All 740 regression tests pass. Ruff and Mypy are clean. Zero existing files were modified beyond additive `__init__.py` exports. The architecture remains fully compatible with all protected boundaries from S17 through S24.

---

## 2. What Existed Before S25

### S23 — External Information (v2.0)
NAV could acquire information from external providers through a governed, replaceable provider boundary. Contracts included `ExternalInformationRequest`, `ExternalInformationResult`, `ExternalInformationItem`, `SourceMetadata`, and `RetrievalStatus`. Honesty invariants prevented fake research.

### S24 — Evidence Representation (v2.1)
NAV could transform S23 acquisition results into structured `Evidence` objects with:
- Direct `SourceMetadata` references (no provenance duplication)
- Qualitative `EvaluationState` (UNASSESSED, SUPPORTED, CONTRADICTED, CONFLICTED, UNCERTAIN)
- Explicit `EvidenceRelation` recording (SUPPORTS, CONTRADICTS, CORROBORATES, DERIVED_FROM)
- Full `EvidenceTrace` provenance chains
- In-memory `EvidenceStore`

### The Gap
S24 could represent that Evidence A supports Evidence B and Evidence C contradicts Evidence A. However, there was no structured mechanism for asking: **"Given this collection of evidence, what finding can NAV responsibly derive?"** The relationships existed but no synthesis consumed them.

---

## 3. What Was Missing

| Capability | S24 Status | S25 Requirement |
|---|---|---|
| Structured finding output | ❌ Not present | Deterministic `Finding` contract |
| Support aggregation | ❌ Not present | Classify evidence by relation role |
| Conflict representation | ❌ Not present | Honest `CONTESTED` status |
| Insufficient evidence handling | ❌ Not present | Explicit `INSUFFICIENT_EVIDENCE` state |
| Synthesis provenance | ❌ Not present | `evidence_basis` trace to S24/S23 |
| Epistemic uncertainty | ❌ Not present | No manufactured certainty |

---

## 4. What Was Built

### 4.1 New Contracts — `core/contracts/finding.py`

**`FindingState`** (Enum, 4 values):
- `SUPPORTED` — All related evidence supports; no contradictions recorded
- `CONTESTED` — Evidence contains both supporting and contradicting signals
- `INCONCLUSIVE` — Evidence exists but relationships are insufficient to conclude
- `INSUFFICIENT_EVIDENCE` — No evidence was provided for synthesis

**`Finding`** (Frozen dataclass, 9 fields):
- `finding_id` — Unique identifier
- `claim` — The claim or question being evaluated
- `status` — The synthesized `FindingState`
- `supporting_evidence` — Tuple of evidence IDs with supporting relations
- `contradicting_evidence` — Tuple of evidence IDs with contradicting relations
- `uncertainty` — Human-readable description of remaining uncertainty
- `evidence_basis` — All evidence IDs considered during synthesis
- `derived_at` — Synthesis timestamp
- `synthesis_basis` — Explanation of derivation methodology

All fields are immutable after construction. Validation rejects empty `finding_id` and `claim`.

### 4.2 Synthesis Engine — `capabilities/evidence/synthesis.py`

**`EvidenceSynthesizer`** class with a single public method:

```python
def synthesize(evidence_ids: list[str], claim: str) -> Finding
```

**Processing pipeline:**
1. Validate claim is non-empty
2. Deduplicate input evidence IDs
3. Handle empty input → `INSUFFICIENT_EVIDENCE`
4. Validate all evidence IDs exist in S24 store (reject ghost evidence)
5. Collect internal relations (both endpoints within the evidence set)
6. Classify evidence by relation role:
   - `SUPPORTS` / `CORROBORATES` → supporting set
   - `CONTRADICTS` → contradicting set
   - `DERIVED_FROM` → informational only, does not affect status
7. Determine status deterministically:
   - Any contradictions → `CONTESTED`
   - Support only → `SUPPORTED`
   - No relevant relations → `INCONCLUSIVE`
8. Generate uncertainty description and synthesis basis
9. Return frozen `Finding`

### 4.3 Test Suite — `tests/test_s25_synthesis.py`

**38 tests** across 9 test classes:

| Test Class | Count | Coverage |
|---|---|---|
| `TestBasicSynthesis` | 4 | Single/multiple support, inconclusive states |
| `TestContradictionHandling` | 4 | Support+contradiction, pure contradiction, unresolved conflict, multiple contradictions |
| `TestInsufficientEvidence` | 5 | Empty set, missing IDs, partial missing, empty/whitespace claims |
| `TestRelationTypes` | 4 | SUPPORTS, CORROBORATES, CONTRADICTS, DERIVED_FROM |
| `TestProvenance` | 4 | Evidence basis completeness, sorting, S24 trace, S23 provenance chain |
| `TestIntegrity` | 1 | Failed S23 acquisition → no ghost evidence |
| `TestDeterminism` | 3 | Same input → same output, deduplication |
| `TestImmutability` | 4 | Frozen Finding, frozen claim, ID/claim validation |
| `TestS23ToS25Integration` | 2 | Full S23→S24→S25 pipeline, contested finding from pipeline |
| `TestS24BehaviorPreserved` | 5 | Evidence construction, service, evaluation, relations, trace |
| `TestS23BehaviorPreserved` | 2 | Static provider, honesty invariant |

### 4.4 Additive Exports

- `core/contracts/__init__.py` — Added `Finding`, `FindingState` to public API
- `capabilities/evidence/__init__.py` — Added `EvidenceSynthesizer` alongside `EvidenceService`

---

## 5. Architectural Boundaries Preserved

| Protected System | Sprint | Status |
|---|---|---|
| Work | S17 | ✅ Untouched |
| Human Control | S18 | ✅ Untouched |
| Interaction | S19 | ✅ Untouched |
| Security | S20 | ✅ Untouched — no new authorization |
| Environment | S21 | ✅ Untouched |
| Integration | S22 | ✅ Untouched |
| External Information | S23 | ✅ Untouched — consumed via S24 |
| Evidence | S24 | ✅ Untouched — consumed, not modified |

**No existing file was modified** beyond the two `__init__.py` export additions. All S24 contracts, the `EvidenceService`, `EvidenceStore`, `EvidenceEvaluator`, and `EvidenceRelationDetector` remain byte-identical to their v2.1 state.

---

## 6. What Changed vs. What Did Not Change

### Changed (Additive Only)
| File | Nature |
|---|---|
| `core/contracts/finding.py` | **New** — Finding contracts |
| `capabilities/evidence/synthesis.py` | **New** — Synthesis engine |
| `tests/test_s25_synthesis.py` | **New** — 38 tests |
| `core/contracts/__init__.py` | **Modified** — Added Finding exports |
| `capabilities/evidence/__init__.py` | **Modified** — Added EvidenceSynthesizer export |
| `docs/s25/*` | **New** — Sprint documentation |
| `docs/architecture/decisions/0014-s25-evidence-synthesis.md` | **New** — ADR |

### Not Changed
- All S23 contracts and providers
- All S24 contracts, service, store, evaluator, relations, factory
- Orchestrator
- Security service
- Research capability (S7/S8 `EvidenceSynthesizer` using LLM — completely separate system)
- Memory subsystem
- All v1 baseline systems
- `pyproject.toml`

---

## 7. How Findings Are Generated

```
Caller provides:
    evidence_ids = ["ev-1", "ev-2", "ev-3"]
    claim = "X occurred in 2020."
         │
         ▼
EvidenceSynthesizer.synthesize()
         │
    ┌────┴────┐
    │ Validate │ → Reject empty claims, missing evidence IDs
    └────┬────┘
         ▼
    ┌────────────┐
    │ Deduplicate │ → Remove duplicate IDs, preserve order
    └────┬───────┘
         ▼
    ┌──────────────┐
    │ Empty check   │ → Return INSUFFICIENT_EVIDENCE if no IDs
    └────┬─────────┘
         ▼
    ┌──────────────────┐
    │ Collect relations │ → Query S24 store for internal relations
    └────┬─────────────┘
         ▼
    ┌───────────────┐
    │ Classify       │ → SUPPORTS/CORROBORATES → supporting set
    │                │ → CONTRADICTS → contradicting set
    │                │ → DERIVED_FROM → informational only
    └────┬──────────┘
         ▼
    ┌───────────────┐
    │ Determine      │ → Contradictions present → CONTESTED
    │ status         │ → Support only → SUPPORTED
    │                │ → No relations → INCONCLUSIVE
    └────┬──────────┘
         ▼
    ┌───────────────┐
    │ Build Finding  │ → Frozen dataclass with full provenance
    └───────────────┘
```

The process is **fully deterministic**. Same input always produces the same status, supporting set, contradicting set, uncertainty text, and synthesis basis. Only `finding_id` (UUID) and `derived_at` (timestamp) vary between calls.

---

## 8. How Uncertainty Is Represented

Uncertainty is represented at two levels:

**Structural** — The `FindingState` enum provides a bounded qualitative classification:
- `SUPPORTED` does not mean "true." It means "all recorded relations support; no contradictions found." The uncertainty text explicitly states: *"Retrieved evidence does not constitute verified truth."*
- `CONTESTED` means "the evidence disagrees and the system has not resolved the conflict."
- `INCONCLUSIVE` means "evidence exists but no explicit relationships connect the items."
- `INSUFFICIENT_EVIDENCE` means "no evidence was provided."

**Textual** — The `uncertainty` field provides a human-readable description generated deterministically from the relation counts. For example:
> *"Evidence contains 2 supporting and 1 contradicting items. The conflict remains unresolved."*

**No numerical confidence scores** are produced. The sprint plan (§14) explicitly prohibits arbitrary formulas like `confidence = 0.842` without principled interpretation.

---

## 9. How Provenance Is Preserved

The full provenance chain survives synthesis:

```
Finding
  │
  ├── evidence_basis = ("ev-1", "ev-2", "ev-3")
  │         │
  │         ▼
  │    EvidenceService.get_evidence("ev-1")
  │         │
  │         ▼
  │    Evidence
  │      ├── claim
  │      ├── source_metadata ──────┐
  │      ├── acquisition_provider_id
  │      └── acquisition_request_id
  │                                │
  │                                ▼
  │                     SourceMetadata (S23)
  │                       ├── source_name
  │                       ├── source_url
  │                       ├── provider_id
  │                       ├── retrieved_at
  │                       └── query_echo
  │
  ├── supporting_evidence = ("ev-1", "ev-2")
  └── contradicting_evidence = ("ev-3")
```

A caller can always answer: **"Which evidence caused NAV to reach this finding?"** by iterating `finding.evidence_basis` and calling `EvidenceService.trace(eid)` for each ID.

---

## 10. How Conflicts Are Represented

Conflicts are **preserved, not resolved**. When evidence contains both supporting and contradicting relations:

```python
Finding(
    status=FindingState.CONTESTED,
    supporting_evidence=("ev-a", "ev-b"),
    contradicting_evidence=("ev-c"),
    uncertainty="Evidence contains 2 supporting and 1 contradicting items. "
                "The conflict remains unresolved.",
)
```

The system does **not**:
- Arbitrarily choose a side
- Weight sources by numerical trust scores
- Declare a "winner" based on count
- Collapse the conflict into a single truth value

This is the most important semantic guarantee of S25 (§5, §19).

---

## 11. What Remains Outside Scope

The following were explicitly deferred to future sprints:

| Capability | Reason for Deferral |
|---|---|
| LLM-assisted semantic reasoning | S25 establishes deterministic baseline first (§29) |
| Automatic NLP contradiction detection | S24 relations are explicit; S25 consumes them (§13) |
| Numerical confidence scoring | No defensible calculation method exists yet (§14) |
| Source independence analysis | Architecture avoids claiming independence from count alone (§15) |
| Persistent finding storage | S24 is in-memory; persistence is a separate architectural question (§28) |
| Orchestrator-facing synthesis capability | Internal subsystem, matching S24 ADR D5 pattern (§22) |
| Integration with Research capability's LLM synthesis | Separate system with separate contracts; future integration possible |

---

## 12. Quality Gate

| Requirement | Status |
|---|---|
| Reconnaissance complete | ✅ |
| Existing architecture understood | ✅ |
| Finding/synthesis model justified | ✅ |
| Evidence relationships correctly consumed | ✅ |
| Support represented | ✅ |
| Conflict represented | ✅ |
| Insufficient evidence represented | ✅ |
| Provenance preserved | ✅ |
| No ghost evidence | ✅ |
| Deterministic behavior | ✅ |
| S24 behavior preserved | ✅ |
| v2.0/S23 behavior preserved | ✅ |
| v1 behavior preserved | ✅ |
| Focused S25 tests pass (38/38) | ✅ |
| Full regression passes (740 passed, 1 skipped, 2 deselected) | ✅ |
| Ruff clean | ✅ |
| Mypy clean (38 source files) | ✅ |
| Documentation complete | ✅ |
| ADR 0014 complete | ✅ |
| Git history clean | ✅ |
| Ready for v2.2 tag | ✅ |

---

## 13. Test Results Summary

```
S25 Tests:      38 passed, 0 failed
Full Suite:    740 passed, 1 skipped, 2 deselected
Regression:      0 failures (baseline: 702 passed → 740 passed)
Ruff:            All checks passed
Mypy:            Success: no issues found in 38 source files
```

---

## 14. Files Delivered

### New Files
- `core/contracts/finding.py`
- `capabilities/evidence/synthesis.py`
- `tests/test_s25_synthesis.py`
- `docs/s25/S25-plan.md`
- `docs/s25/S25-recon-notes.md`
- `docs/s25/baseline.md`
- `docs/s25/implementation.md`
- `docs/s25/completion-report.md`
- `docs/s25/post-completion-report.md`
- `docs/architecture/decisions/0014-s25-evidence-synthesis.md`

### Modified Files (Additive Exports Only)
- `core/contracts/__init__.py` — Added `Finding`, `FindingState`
- `capabilities/evidence/__init__.py` — Added `EvidenceSynthesizer`

### Unmodified Files
- All other files in the repository remain identical to `v2.1`

---

## 15. Recommended Next Steps

1. **Merge** `feature/s25-evidence-synthesis` into `main`
2. **Tag** `v2.2`
3. **S26 consideration:** Evaluate whether AI-assisted semantic relation suggestion should be layered on top of the deterministic S25 foundation
4. **S26 consideration:** Evaluate persistence requirements based on actual usage patterns

---

## 16. S25 North Star — Achieved

> **Give NAV a deterministic foundation for deriving explicit, traceable findings from multiple pieces of evidence while preserving disagreement and uncertainty instead of hiding them.**

S23 gave NAV the ability to **Acquire**.
S24 gave NAV the ability to **Represent and Trace**.
S25 gives NAV the ability to **Synthesize**.

The next step in the long-term trajectory (`COMPARE → REASON → DECIDE → ACT`) remains available for future sprints to build upon this stable, honest, deterministic foundation.

---

**Respectfully submitted for senior review.**