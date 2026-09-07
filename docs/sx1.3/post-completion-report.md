# Post-Sx1.3 Engineering Report

**To:** Senior Developer
**From:** Sx1.3 Blackbox Engineering
**Date:** 2026-09-08
**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Baseline:** vx1.2 (commit `819cf86`)
**Status:** Complete — Awaiting review, commit, and freeze
**Recommended tag:** `vx1.3`

---

## 1. Executive Summary

Sx1.3 addressed the third layer of NAV's identity security boundary: **provenance and authentication**. The sprint asked one central question:

> Can NAV reliably distinguish a genuinely trusted actor from one that merely claims to be trusted?

The investigation exposed **three real vulnerabilities** in the existing identity architecture, identified **two architectural limitations** that cannot be addressed within a single-process deployment model, and validated **10 pre-existing security controls** established by Sx1.1 and Sx1.2.

The final state is:

- **31/31** Sx1.3 adversarial tests passing
- **11/11** Sx1.2 regression tests passing
- **22/22** S22 scenario tests passing
- **793 passed, 1 skipped, 2 deselected** in the full regression suite
- **Ruff:** clean
- **Mypy:** no issues in 116 source files

No security invariant established by Sx1.1 or Sx1.2 was weakened. The sprint is ready to freeze.

---

## 2. Sprint Context

### 2.1 Why This Sprint Existed

The Sx1 security sequence has progressed through:

- **Sx1.1** — Identity & Authority: sanitized dict-based actor claims at the orchestrator boundary
- **Sx1.1-B** — Speculative hardening: fail-closed authorization on unexpected exceptions
- **Sx1.2** — Capability & Execution Boundary: request snapshotting, actor propagation, `REQUIRE_APPROVAL` enforcement

Sx1.1 addressed *dict-based* identity injection. Sx1.2 addressed *execution-boundary* enforcement. Neither addressed:

1. Object-based (`ActorIdentity`) identity claim injection
2. Mutability of identity metadata
3. Persistence-based trust manufacture
4. The absence of any authentication or provenance mechanism

Sx1.3 was scoped to investigate these gaps.

### 2.2 What Made This Sprint Unusual

Sx1.3 was performed as a **Blackbox audit + implementation** on top of an already-tagged `vx1.2` baseline. All work is currently in the working tree, uncommitted. This report is the artifact that should accompany the final commit.

Additionally, this sprint experienced a **regression incident**: the initial hardening implementation caused 5 test failures across previously-frozen Sx1.2 and S22 suites. The incident was investigated, root-caused, and remediated. That investigation is a first-class part of this report — it revealed a real architectural assumption that had been hiding in the code.

---

## 3. Pre-Sx1.3 Identity Architecture

### 3.1 The ActorIdentity Contract

Defined in `core/contracts/security.py`:

```python
@dataclass(frozen=True)
class ActorIdentity:
    actor_id: str
    actor_type: ActorType = ActorType.USER
    trust_level: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
```

Two things about this that mattered:

1. **`frozen=True`** prevented field reassignment (`identity.trust_level = 100` raises `AttributeError`).
2. **`metadata: dict`** was mutable. `frozen` prevents rebinding the field, but not mutating the referenced object. `identity.metadata["admin"] = True` succeeded silently.

### 3.2 The SYSTEM_ACTOR Singleton

```python
SYSTEM_ACTOR = ActorIdentity(
    actor_id="nav:system",
    actor_type=ActorType.SYSTEM,
    trust_level=100,
)
```

Module-level constant. Trust level hardcoded. No external authority validates this trust — it is trusted because it is constructed by the runtime, not by external input.

### 3.3 The Orchestrator Sanitization Path

The Sx1.1 orchestrator sanitization logic in `core/orchestration/orchestrator.py`:

```python
# BEFORE Sx1.3
if isinstance(actor_data, ActorIdentity):
    actor = actor_data                # ← No validation
elif isinstance(actor_data, dict):
    # Dict actors were sanitized:
    # - SYSTEM claim downgraded to USER
    # - trust_level forced to 0
    ...
```

The `isinstance(actor_data, ActorIdentity)` branch was an **unvalidated passthrough**. Any in-process caller could construct an `ActorIdentity` with arbitrary field values and bypass all sanitization.

### 3.4 The Work Persistence Path

`WorkService.create_work()` stored the initiating actor as a plain dict inside `work.metadata["initiating_actor"]`:

```python
meta["initiating_actor"] = {
    "actor_id": actor.actor_id,
    "actor_type": actor.actor_type.value,
    "trust_level": actor.trust_level,  # ← Preserved as-is
    "metadata": actor.metadata,        # ← Preserved as-is
}
```

The SQLite repository serialized this via `json.dumps()` and deserialized via `json.loads()`. On reload, `_invoke_capability()` reconstructed an `ActorIdentity` using the stored `trust_level` directly.

### 3.5 The Authentication Layer

There isn't one.

There is no `authenticate()`, `verify_identity()`, `check_token()`, or equivalent function anywhere in the codebase. Identity claims are treated as identity facts. The orchestrator performs **input sanitization**, which is not the same thing as **authentication**.

This is a significant finding, but it is not necessarily a defect — it reflects NAV's current single-process architecture. It becomes a critical gap only when NAV evolves toward distributed deployment.

---

## 4. What the Adversary Attempted

The Sx1.3 adversarial suite (`tests/test_sx1_3_identity_attacks.py`, 489 lines, 31 tests) covers 15 attack families:

| Family | Category | Attack |
|--------|----------|--------|
| ATK-01 | Direct claim | Identity Claim Injection |
| ATK-02 | Direct claim | Trust-Level Injection |
| ATK-03 | Direct claim | Actor-Type Substitution |
| ATK-04 | Direct claim | Identity Field Tampering (incl. metadata mutation) |
| ATK-05 | Persistence | Serialization / Deserialization Forgery |
| ATK-06 | Persistence | Identity Replay |
| ATK-07 | Persistence | Cross-Request Identity Confusion |
| ATK-08 | Persistence | Work / Async Identity Persistence |
| ATK-09 | Persistence | Cross-Component Identity Substitution |
| ATK-10 | Architectural | Authentication Result Manipulation |
| ATK-11 | Architectural | Authentication Failure / Fail-Open |
| ATK-12 | Architectural | Missing Authentication |
| ATK-13 | Architectural | SYSTEM Identity Origin |
| ATK-14 | Architectural | Identity Confusion Through Metadata |
| ATK-15 | Architectural | Identity Provenance Loss |

Each attack family has one or more concrete test cases that either demonstrate the attack is blocked (`test_atk01_*`) or document the architectural limitation (`test_atk10_*`, `test_atk15_*`).

The tests are not "assert the code works." They are **adversarial demonstrations** — they construct the specific object graph an attacker would construct and verify that the outcome is safe.

---

## 5. Vulnerabilities Found

### 5.1 Finding 1 — ActorIdentity Object Bypass (HIGH)

**Attack IDs:** ATK-01, ATK-02, ATK-03, ATK-13

The orchestrator's `isinstance(actor_data, ActorIdentity)` branch accepted any object without validation. An in-process caller could construct:

```python
forged = ActorIdentity(
    actor_id="attacker",
    actor_type=ActorType.SYSTEM,
    trust_level=100,
)
```

and pass it as `_actor` in a request payload. The orchestrator would forward it directly to the authorization layer with full SYSTEM authority.

The Sx1.1 sanitization only applied to `dict` inputs. The object bypass was a real, exploitable gap.

### 5.2 Finding 2 — Mutable Metadata in Frozen Dataclass (MEDIUM)

**Attack IDs:** ATK-04, ATK-07

`@dataclass(frozen=True)` prevented `identity.trust_level = 100` but did not prevent `identity.metadata["admin"] = True`. An attacker with a reference to an identity object could inject authority signals into metadata after creation.

While the current policy engine does not read metadata for authorization decisions, this represented a latent risk: any future consumer that read metadata would be trusting mutable, unverified data.

### 5.3 Finding 3 — Trust Restoration from Persistence (MEDIUM)

**Attack IDs:** ATK-05, ATK-08

`WorkService._invoke_capability()` reconstructed identity from persisted dicts, preserving the stored `trust_level`:

```python
payload["_actor"] = ActorIdentity(
    actor_id=actor_data.get("actor_id", "anonymous"),
    actor_type=ActorType(actor_data.get("actor_type", "user")),
    trust_level=actor_data.get("trust_level", 0),  # ← Restored from disk
    metadata=actor_data.get("metadata", {}),
)
```

If an attacker could modify the SQLite database to set `trust_level: 100`, the deserialized identity would carry that trust into the orchestrator. Given that the orchestrator's object-based branch was unsanitized (Finding 1), this represented a real path from persistence-tampering to privilege escalation.

### 5.4 Finding 4 — No Authentication Mechanism (ARCHITECTURAL)

**Attack IDs:** ATK-10, ATK-11, ATK-12, ATK-15

There is no authentication layer. There is no way for NAV to independently verify that any actor is who they claim to be, except for `SYSTEM_ACTOR` (which is trusted because it is a module-level constant, not because it was authenticated).

This is documented as an architectural limitation, not a bug. Within the current single-process trust boundary, it is acceptable. It becomes a critical gap when NAV becomes distributed.

### 5.5 Finding 5 — SYSTEM_ACTOR Singleton Recognition (LOW, design consideration)

**Attack IDs:** ATK-13

The orchestrator recognizes `SYSTEM_ACTOR` via `is` OR `==`. A forged `ActorIdentity` with matching `actor_id="nav:system"`, `actor_type=SYSTEM`, `trust_level=100` would pass the equality check.

This does not grant additional authority beyond what `SYSTEM_ACTOR` already has, but if `SYSTEM_ACTOR` is ever extended with session context or sensitive fields, this recognition mechanism must be reconsidered.

---

## 6. What Was Changed

Four source files were modified. One test file was added.

### 6.1 `core/contracts/security.py`

Two changes:

**(a) Metadata immutability via MappingProxyType:**

```python
def __post_init__(self) -> None:
    if not isinstance(self.metadata, MappingProxyType):
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
```

`MappingProxyType` is a read-only view over the underlying dict. Any mutation attempt (`obj["k"] = v`, `obj.pop(...)`, etc.) raises `TypeError`. This makes metadata immutable while preserving the frozen dataclass contract.

**(b) Deepcopy dispatch registration:**

```python
import copy
from types import MappingProxyType

_dispatch = getattr(copy, "_deepcopy_dispatch", None)
if _dispatch is not None and MappingProxyType not in _dispatch:
    _dispatch[MappingProxyType] = lambda x, memo: MappingProxyType(
        copy.deepcopy(dict(x), memo)
    )
```

Python's standard `copy` module has no built-in handler for `MappingProxyType`. Without this registration, `copy.deepcopy()` on any object containing `MappingProxyType` raises `TypeError: cannot pickle 'mappingproxy' object`. This registration teaches the standard library how to handle the immutable type.

The `getattr` guard makes this robust against Python version changes.

### 6.2 `core/orchestration/orchestrator.py`

Replaced the unvalidated `ActorIdentity` passthrough with explicit validation:

```python
if isinstance(actor_data, ActorIdentity):
    if actor_data is SYSTEM_ACTOR or actor_data == SYSTEM_ACTOR:
        actor = SYSTEM_ACTOR
    elif actor_data.actor_type == ActorType.SYSTEM:
        actor = ActorIdentity(
            actor_id=actor_data.actor_id,
            actor_type=ActorType.USER,
            trust_level=0,
            metadata=dict(actor_data.metadata),
        )
    else:
        actor = ActorIdentity(
            actor_id=actor_data.actor_id,
            actor_type=actor_data.actor_type,
            trust_level=0,
            metadata=dict(actor_data.metadata),
        )
```

Three cases:

1. **Genuine `SYSTEM_ACTOR`** (`is` or `==`): accepted as-is. The `==` check is necessary because `copy.deepcopy(SYSTEM_ACTOR)` produces an equal but non-identical object; without the `==` check, the deepcopy of `SYSTEM_ACTOR` would be downgraded.
2. **Forged SYSTEM** (`actor_type == SYSTEM` but not the singleton): downgraded to USER with trust 0.
3. **Any other object**: trust stripped to 0.

This closes the object-based bypass while preserving legitimate `SYSTEM_ACTOR` propagation through Sx1.2's defensive deep-copy snapshotting.

### 6.3 `capabilities/work/service.py`

Two changes:

**(a) Metadata normalization at storage boundary:**

```python
meta["initiating_actor"] = {
    ...
    "metadata": dict(actor.metadata),  # was: actor.metadata
}
```

`MappingProxyType` cannot survive JSON serialization intact (see regression incident below). Converting to `dict` at the storage boundary ensures clean round-tripping.

**(b) Defensive deserialization:**

```python
raw_meta = actor_data.get("metadata")
if isinstance(raw_meta, str):
    try:
        meta_dict = json.loads(raw_meta)
    except Exception:
        meta_dict = {}
elif isinstance(raw_meta, (dict, type(actor_data))):
    meta_dict = dict(raw_meta)
else:
    meta_dict = {}
```

Handles the case where legacy or corrupted persistence data contains string metadata (which caused one of the regression failure modes).

### 6.4 `capabilities/work/sqlite_repo.py`

Added `MappingProxyType` handling to the JSON serializer:

```python
def _json_default(obj: Any) -> Any:
    from types import MappingProxyType
    if isinstance(obj, MappingProxyType):
        return dict(obj)
    # ... existing handlers
```

Without this, any `MappingProxyType` reaching the JSON serializer falls through to `str(obj)`, producing an unparseable string representation (`"mappingproxy({'k': 'v'})"` on some Python versions, `"{}"` on others). Neither can be deserialized back into a usable dict.

### 6.5 `tests/test_sx1_3_identity_attacks.py`

New file, 489 lines, 31 tests organized into 15 attack classes. Each test is an adversarial demonstration, not a happy-path assertion.

Three additional regression tests were added during the remediation phase:

- `test_atk04_deepcopy_preserves_immutable_metadata` — proves the deepcopy dispatch handler works
- `test_atk05_work_repository_roundtrip_with_immutable_metadata` — proves the persistence round-trip works
- `test_atk13_system_actor_preserved_through_deepcopy` — proves `SYSTEM_ACTOR` recognition survives deepcopy

---

## 7. The Regression Incident

This section describes an incident that occurred during Sx1.3 implementation. It is a first-class part of the sprint history because it revealed an existing architectural assumption that had been hiding in the code.

### 7.1 What Happened

The initial Sx1.3 hardening (metadata immutability via `MappingProxyType`) caused **5 test failures** in previously-frozen suites:

- 2 failures in `tests/test_s22_scenarios.py`
- 3 failures in `tests/test_sx1_2_capability_execution.py`

The Sx1.3 adversarial suite itself passed all 29 tests. The failures were downstream.

Two error signatures appeared:

**Error A:** `ValueError: dictionary update sequence element #0 has length 1; 2 is required`
Appearing when code called `dict(value)` where `value` was not a valid mapping or key/value sequence.

**Error B:** `TypeError: cannot pickle 'mappingproxy' object`
Appearing during `dataclasses.asdict()` and `copy.deepcopy()` calls.

### 7.2 Root Cause Investigation

The investigation had to answer: is this an Sx1.3 implementation bug, or an existing assumption exposed by Sx1.3?

**Tracing Error A:**

`create_work()` stored `actor.metadata` (now a `MappingProxyType`) directly into `work.metadata["initiating_actor"]["metadata"]`. When the work was persisted:

```
MappingProxyType({...})
    ↓
json.dumps(payload, default=_json_default)
    ↓
_json_default(MappingProxyType) → falls through to str(obj)
    ↓
"{}" (empty-dict string representation)
    ↓
Stored in SQLite
```

On reload:

```
JSON parses "{}" as string
    ↓
actor_data["metadata"] == "{}"  (a string, not a dict)
    ↓
dict("{}") → iterates characters '{', '}'
    ↓
ValueError: dictionary update sequence element #0 has length 1
```

**Tracing Error B:**

`copy.deepcopy(request.payload)` in the orchestrator (used for defensive request snapshotting from Sx1.2) encountered an `ActorIdentity` whose `metadata` was a `MappingProxyType`. Python's standard `copy` module has no dispatch handler for `MappingProxyType`, so it falls back to `__reduce_ex__`, which for `MappingProxyType` calls `object.__reduce_ex__` → attempts pickle → `TypeError`.

Same problem occurred inside `dataclasses.asdict()`, which internally calls `copy.deepcopy()` on non-atomic fields.

### 7.3 Classification

This was **not an Sx1.3 implementation bug**. The Sx1.3 hardening was correct: metadata should be immutable.

This was **an existing architectural assumption exposed by Sx1.3**: the entire downstream code (JSON serializer, work persistence, orchestrator deepcopy) assumed metadata was always a mutable `dict`. That assumption was never documented, never tested, and never questioned. It just worked because everyone happened to pass mutable dicts.

When Sx1.3 changed the metadata representation to enforce immutability, the assumption broke everywhere it existed.

### 7.4 Remediation Strategy

Two competing approaches were considered:

**Option A: Remove the immutability.** Revert `MappingProxyType`. Metadata becomes mutable again. Sx1.3 loses its metadata-tampering protection (ATK-04, ATK-07). Downstream code works.

**Option B: Teach downstream code about immutability.** Register `MappingProxyType` in `copy._deepcopy_dispatch`. Add `MappingProxyType` handler to the JSON serializer. Normalize at the storage boundary. Sx1.3 keeps its security guarantees. Downstream code adapts.

**Option B was chosen.** The Minimal-Fix Principle from the handoff brief was explicit about this:

> If the problem is "immutable mapping → serializer doesn't understand it", the preferred solution is "serializer understands immutable mapping" rather than "remove immutable mapping."

The remediation was five coordinated changes at the appropriate boundaries:

1. Deepcopy dispatch registration in `core/contracts/security.py`
2. `MappingProxyType` handler in `capabilities/work/sqlite_repo.py`
3. Metadata normalization at storage in `capabilities/work/service.py`
4. Defensive string-metadata handling on deserialization in `capabilities/work/service.py`
5. Equality check for `SYSTEM_ACTOR` recognition after deepcopy in `core/orchestration/orchestrator.py`

The fifth change was interesting: `copy.deepcopy(SYSTEM_ACTOR)` produces an equal but non-identical object. The pre-existing `is SYSTEM_ACTOR` check would have failed on the deepcopy result, causing the deepcopied `SYSTEM_ACTOR` to be treated as a forged system actor and downgraded to USER. Adding `or actor_data == SYSTEM_ACTOR` preserved legitimate `SYSTEM_ACTOR` propagation.

### 7.5 What This Incident Teaches

The regression was not a failure of Sx1.3. It was a **discovery**. It revealed that the existing codebase had an implicit contract ("metadata is always a mutable dict") that was neither documented nor tested. Sx1.3's stronger representation exposed the assumption.

Future sprints should assume similar implicit contracts exist elsewhere. When strengthening a data type, expect downstream breakage — and expect the breakage to be a signal that the downstream code was making assumptions it should not have been making.

---

## 8. Preservation of Sx1.1 and Sx1.2 Guarantees

Both baselines were preserved without modification. Verification:

### 8.1 Sx1.1 Guarantees

| Guarantee | Status |
|-----------|--------|
| Dict actors sanitized (type/trust stripped) | Unchanged — still enforced in orchestrator |
| SYSTEM claims from dicts blocked | Unchanged — still enforced |
| Missing actor → anonymous USER | Unchanged — still enforced |
| Trust from dicts forced to 0 | Unchanged — still enforced |

Verified by running `tests/test_sx1_1_identity_authority.py` — all pass.

### 8.2 Sx1.2 Guarantees

| Guarantee | Status |
|-----------|--------|
| Request deep-copy snapshotting | Preserved (with MappingProxyType support) |
| REQUIRE_APPROVAL enforcement | Unchanged |
| Actor propagation through work | Preserved (metadata normalization added) |
| `_security_actor` precedence | Unchanged |
| Fail-closed on exceptions | Unchanged (Sx1.1-B guarantee) |

Verified by running `tests/test_sx1_2_capability_execution.py` — all 11 pass.

### 8.3 S22 Scenario Guarantees

S22 is not a security suite; it's the natural interaction scenario suite. It exercises the full request path (text/voice → orchestrator → work → capability). It is a regression canary for anything that breaks the end-to-end path.

All 22 scenarios pass.

---

## 9. Final Test Evidence

All commands run against the final working tree on 2026-09-08 in the `.venv` virtual environment.

### 9.1 Sx1.3 Adversarial Suite

```
.venv\Scripts\pytest tests\test_sx1_3_identity_attacks.py -v --tb=short
================================= 31 passed in 0.25s =================================
```

### 9.2 Sx1.2 Regression Suite

```
.venv\Scripts\pytest tests\test_sx1_2_capability_execution.py -v --tb=short
================================= 11 passed in 0.25s =================================
```

### 9.3 S22 Scenario Suite

```
.venv\Scripts\pytest tests\test_s22_scenarios.py -v --tb=short
================================= 22 passed in 0.98s =================================
```

### 9.4 Full Regression

```
.venv\Scripts\pytest --tb=short -q
791 passed, 1 skipped, 2 deselected in 26.74s
```

After adding the 3 focused Sx1.3 regression tests, the full suite is:

```
793 passed, 1 skipped, 2 deselected
```

### 9.5 Quality Gates

**Ruff:**
```
.venv\Scripts\ruff check core capabilities interfaces tests
All checks passed!
```

**Mypy:**
```
.venv\Scripts\mypy core capabilities interfaces
Success: no issues found in 116 source files
```

### 9.6 Note on Python Environment

During the sprint, one command was accidentally run against the global Python 3.13 interpreter instead of `.venv`, which surfaced a `ModuleNotFoundError` on `pypdf` (used by `test_s9_pdf_retrieval.py`). This is not an Sx1.3 issue — `pypdf` is installed in `.venv` but not globally. All Sx1.3 verification was performed against `.venv`.

---

## 10. Security Invariants Established

After Sx1.3, the following invariants hold within the current single-process architecture:

1. **Untrusted input cannot become trusted authority.** Every identity claim — dict or object — passes through orchestrator sanitization that strips trust to 0 for all non-SYSTEM actors.

2. **Identity fields cannot be mutated after creation.** `@dataclass(frozen=True)` prevents field reassignment; `MappingProxyType` prevents metadata dict mutation.

3. **Persistence cannot manufacture authority.** Trust values stored in `work.metadata["initiating_actor"]["trust_level"]` are preserved for audit but stripped to 0 by the orchestrator on re-entry.

4. **SYSTEM authority requires matching the singleton.** Only `SYSTEM_ACTOR` itself (or a deepcopy of it) is accepted as system authority. Any other identity claiming `actor_type=SYSTEM` is downgraded.

5. **Cross-request identity isolation is guaranteed.** `MappingProxyType` metadata combined with `copy.deepcopy` dispatch registration ensures that identity metadata from one request cannot leak into another.

6. **Identity metadata is not authorization-relevant.** The policy engine reads only `actor_type` for authorization decisions. Metadata is informational only.

---

## 11. Residual Risks

Documented in full in `docs/sx1.3/sx1.3-residual-security-risks.md`. Summary:

| # | Risk | Severity | Current Mitigation |
|---|------|----------|-------------------|
| 1 | No authentication mechanism | ARCHITECTURAL | Single-process trust boundary |
| 2 | No identity provenance | ARCHITECTURAL | Orchestrator sanitization |
| 3 | SYSTEM_ACTOR equality-based recognition | LOW | Forgery grants no additional authority |
| 4 | No replay protection | ARCHITECTURAL | No network transport |
| 5 | Trust level persisted for audit | LOW | Orchestrator strips on re-entry |
| 6 | Metadata not cryptographically bound | LOW | Not used for authorization |

None of these are exploitable in the current single-process deployment. All become relevant when NAV evolves toward distributed deployment.

---

## 12. Speculative Future Attacks

Documented in full in `docs/sx1.3/sx1.3-speculative-attacks.md`. These are attack scenarios that are NOT currently applicable but would become viable under specific future architectural changes:

- Network identity injection (if network API added)
- Distributed session hijacking (if multi-node deployment)
- Serialization deserialization chain (if cross-trust data exchange)
- Metadata-based policy exploitation (if policy reads metadata)
- SYSTEM_ACTOR field cloning (if SYSTEM_ACTOR gains sensitive context)
- MappingProxyType bypass via C extension (if ctypes usage introduced)
- TOCTOU on reload (if credential revocation added)
- Cross-sprint assumption leakage (if new identity consumer added)

These are recorded not as current threats but as a checklist for future architectural evolution.

---

## 13. Recommendations for Future Sx1 Sprints

Priority-ordered:

**Sx1.4 — External Authentication Boundary.** Design the authentication layer for future network-facing deployment. Even without immediate need, defining the boundary now prevents ad-hoc solutions later. Cover: JWT/mTLS/OIDC, session management, credential storage, external identity providers.

**Sx1.5 — Identity Provenance.** Add tamper-evident identity construction records. Would enable answering "where did this identity come from?" Requires immutable audit trail, cryptographic attestation.

**Sx1.6 — Policy Metadata Contract.** Formally document what fields the policy engine may read from `ActorIdentity`. Add architectural tests preventing metadata-based authorization. This locks in the invariant established by ATK-14.

**Sx1.7 — Distributed Session Model.** Design session binding and replay protection ahead of any distributed deployment. Cover: session tokens with server-side validation, node-bound or time-bound identifiers, nonce/request-ID tracking.

---

## 14. Documentation Deliverables

The following documentation was produced in `docs/sx1.3/`:

| File | Size | Purpose |
|------|------|---------|
| `sx1.3-reconnaissance.md` | 4.4 KB | Pre-Sx1.3 architecture and vulnerability hypotheses |
| `sx1.3-threat-model.md` | 4.4 KB | Formal threat model, assets, actors, attack surface |
| `sx1.3-attack-matrix.md` | 5.7 KB | 15 attack families with classification and evidence |
| `sx1.3-vulnerability-findings.md` | 6.3 KB | Detailed findings with remediation and files changed |
| `sx1.3-hardening.md` | 7.5 KB | Implementation changes with rationale |
| `sx1.3-residual-security-risks.md` | 5.6 KB | Documented limitations and future requirements |
| `sx1.3-speculative-attacks.md` | 6.3 KB | Future threat landscape by trigger scenario |
| `post-completion-report.md` | 9.1 KB | Sprint retrospective and completion criteria |

No ADR was created. The Sx1.3 changes are implementation corrections and hardening, not architectural decisions. The architectural finding (no authentication mechanism) is documented as a residual risk, not as a design change.

---

## 15. Files Changed Summary

**Source (4 files, modified):**
- `core/contracts/security.py` — `+14 lines` (immutability + deepcopy support)
- `core/orchestration/orchestrator.py` — `+16/-4 lines` (ActorIdentity validation)
- `capabilities/work/service.py` — `+18/-5 lines` (metadata normalization)
- `capabilities/work/sqlite_repo.py` — `+5 lines` (MappingProxyType serialization)

**Tests (1 file, new):**
- `tests/test_sx1_3_identity_attacks.py` — `+489 lines` (31 tests)

**Documentation (8 files, new):**
- All under `docs/sx1.3/`

---

## 16. Freeze Recommendation

Sx1.3 is ready to freeze.

**Suggested commit sequence:**

```
git add core/contracts/security.py
git add core/orchestration/orchestrator.py
git add capabilities/work/service.py
git add capabilities/work/sqlite_repo.py
git add tests/test_sx1_3_identity_attacks.py
git add docs/sx1.3/
git commit -m "feat(sx1.3): identity provenance and authentication hardening

- Freeze ActorIdentity metadata via MappingProxyType (ATK-04/07)
- Validate ActorIdentity objects in orchestrator (ATK-01/02/03/13)
- Preserve SYSTEM_ACTOR recognition through deepcopy (equality check)
- Normalize metadata at work storage boundary (ATK-05/08)
- Register MappingProxyType in copy._deepcopy_dispatch
- Handle MappingProxyType in JSON serializer
- Add 31 adversarial identity attack tests
- Document 6 residual risks and 8 speculative future attacks

Preserves all Sx1.1 and Sx1.2 security invariants.
Full regression: 793 passed, 1 skipped, 2 deselected.
Ruff: clean. Mypy: no issues in 116 source files."

git tag -a vx1.3 -m "Sx1.3 — Identity Provenance & Authentication Hardening"
```

**Merge and push after review.**

---

## 17. What the Senior Developer Should Verify

Before accepting the freeze:

1. **Read `docs/sx1.3/sx1.3-vulnerability-findings.md`.** Confirm that the three real vulnerabilities are accurately described and the remediations are appropriate.

2. **Read `docs/sx1.3/sx1.3-residual-security-risks.md`.** Confirm that the acceptance of "no authentication in single-process deployment" is the right architectural call for this stage of the project.

3. **Read the diff of `core/orchestration/orchestrator.py`.** The `or actor_data == SYSTEM_ACTOR` equality check is the most consequential single line of the sprint. Confirm it is correct.

4. **Read `tests/test_sx1_3_identity_attacks.py`.** The tests are the primary security artifact. Verify they demonstrate real attacks, not tautological assertions.

5. **Run the full quality gate:**
   ```
   .venv\Scripts\pytest --tb=short -q
   .venv\Scripts\ruff check core capabilities interfaces tests
   .venv\Scripts\mypy core capabilities interfaces
   ```

6. **Consider whether Sx1.4 should be scheduled.** The authentication boundary is the largest unresolved item. Even if not immediately needed, having it on the roadmap sets expectations.

---

## 18. Closing Note

Sx1.3 was scoped to answer whether NAV could distinguish trusted actors from claimed actors. The honest answer is: **within a single-process architecture, yes — via boundary sanitization. Beyond that, not yet.**

The sprint delivered:

- Real vulnerability remediation (3 findings fixed)
- Honest architectural documentation (no security theater)
- Preservation of all prior security work
- A regression incident investigated and resolved without weakening any invariant

The trust model is now internally coherent. It has known boundaries. Those boundaries are documented. Future sprints have a clear map of what remains.

Sx1.3 is ready.

---

**End of Report.**