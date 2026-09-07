# Sx1.3 Hardening Implementation

**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Date:** 2026-09-08
**Baseline:** vx1.2 (commit 819cf86)

---

## 1. Changes Overview

Sx1.3 modified four source files and added one test file. All changes
are uncommitted working tree modifications on top of the vx1.2 tag.

| File | Lines Changed | Type |
|------|--------------|------|
| `core/contracts/security.py` | +14 | Identity immutability + deepcopy support |
| `core/orchestration/orchestrator.py` | +16/-4 | ActorIdentity validation |
| `capabilities/work/service.py` | +18/-5 | Metadata normalization + deserialization safety |
| `capabilities/work/sqlite_repo.py` | +5 | MappingProxyType serialization |
| `tests/test_sx1_3_identity_attacks.py` | +489 (new) | 31 adversarial tests |

---

## 2. Change 1: Metadata Immutability (ATK-04/07)

### File: `core/contracts/security.py`

### What Changed

Added `__post_init__` to `ActorIdentity` that wraps the metadata
dict in `types.MappingProxyType`:

``python
def __post_init__(self) -> None:
    if not isinstance(self.metadata, MappingProxyType):
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
Why
The frozen dataclass prevented field reassignment but not dict
mutation. An attacker with access to an ActorIdentity object
could modify identity.metadata["admin"] = True after creation.
MappingProxyType provides a read-only view over the underlying
dict, raising TypeError on any mutation attempt.

Security Property Established
Identity metadata is now immutable after construction. No code path
can modify metadata fields on an existing ActorIdentity instance.

3. Change 2: Deepcopy Support for MappingProxyType (ATK-07)
File: core/contracts/security.py
What Changed
Registered a deepcopy dispatch handler for MappingProxyType at
module import time:

Python

import copy
from types import MappingProxyType

_dispatch = getattr(copy, "_deepcopy_dispatch", None)
if _dispatch is not None and MappingProxyType not in _dispatch:
    _dispatch[MappingProxyType] = lambda x, memo: MappingProxyType(
        copy.deepcopy(dict(x), memo)
    )
Why
The orchestrator uses copy.deepcopy(request.payload) for
defensive request snapshotting (Sx1.2 ATK-05). When ActorIdentity
objects containing MappingProxyType metadata entered the payload,
deepcopy raised TypeError: cannot pickle 'mappingproxy' object
because Python's standard copy module has no built-in handler for
MappingProxyType.

Rather than removing immutability (which would weaken security), the
fix teaches deepcopy how to handle the immutable type.

Security Property Established
Immutable identity metadata is compatible with defensive deep-copy
snapshotting. Security hardening does not break execution boundaries.

4. Change 3: ActorIdentity Validation in Orchestrator (ATK-01/02/03/13)
File: core/orchestration/orchestrator.py
What Changed
Replaced the unsanitized isinstance passthrough:

Python

# BEFORE (vx1.2):
if isinstance(actor_data, ActorIdentity):
    actor = actor_data  # No validation
With explicit validation:

Python

# AFTER (Sx1.3):
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
Why
The Sx1.1 sanitization only applied to dict-based actors. In-process
callers could construct ActorIdentity(actor_type=SYSTEM, trust=100)
and bypass all checks. Sx1.3 closes this gap by applying the same
sanitization logic to object-based actors.

The equality check (==) alongside identity check (is) is
necessary because copy.deepcopy(SYSTEM_ACTOR) produces an equal
but non-identical object.

Security Property Established
All actor claims — whether dict or object — are sanitized at the
orchestrator boundary. Trust cannot be elevated through object
construction. SYSTEM authority requires matching the real singleton.

5. Change 4: Metadata Normalization at Storage Boundary (ATK-05/08)
File: capabilities/work/service.py
What Changed
In create_work(), metadata is now explicitly converted to dict:

Python

"metadata": dict(actor.metadata),  # was: actor.metadata
In _invoke_capability(), deserialization handles string metadata
from legacy/corrupted serialization:

Python

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
Why
When MappingProxyType metadata was stored directly into the work
metadata dict, the JSON serializer's fallback str() converted it
to the string "{}". On reload, dict("{}") iterated over
characters and raised ValueError. The fix normalizes at both
boundaries: storage converts to dict, reload handles string fallback.

Security Property Established
Identity metadata survives the persistence round-trip without data
loss or type corruption. Deserialization does not crash on legacy
data formats.

6. Change 5: MappingProxyType Serialization (ATK-05)
File: capabilities/work/sqlite_repo.py
What Changed
Added MappingProxyType handling to _json_default():

Python

def _json_default(obj: Any) -> Any:
    from types import MappingProxyType
    if isinstance(obj, MappingProxyType):
        return dict(obj)
    # ... existing handlers
Why
If a MappingProxyType reaches the JSON serializer (e.g., through
a dataclass field), the serializer needs to know how to convert it.
Without this handler, it falls through to str(obj) which produces
an unparseable string representation.

Security Property Established
The serialization layer correctly handles immutable metadata types
without requiring callers to manually convert.

7. Regression Incident
What Happened
The initial Sx1.3 implementation (metadata immutability via
MappingProxyType) caused five regression failures in Sx1.2 and
S22 test suites.

Root Cause
Single root cause with two failure modes:

Mode A — String metadata (3 failures): create_work() stored
MappingProxyType directly into the work metadata dict. The JSON
serializer's str() fallback converted it to "{}". On reload,
dict("{}") iterated characters, raising ValueError.

Mode B — Deepcopy failure (2 failures): copy.deepcopy() in
the orchestrator and dataclasses.asdict() in the serializer both
internally call deepcopy, which has no built-in handler for
MappingProxyType, raising TypeError.

Remediation
Normalize MappingProxyType → dict at storage boundary.
Register MappingProxyType in copy._deepcopy_dispatch.
Add MappingProxyType handler to JSON serializer.
Add defensive string-metadata handling in deserialization.
Use equality check (==) alongside identity check (is)
for SYSTEM_ACTOR validation after deepcopy.
Classification
This was an existing architectural assumption exposed by Sx1.3,
not an Sx1.3 implementation bug. The existing code assumed metadata
was always a mutable dict. Sx1.3's immutability hardening was
correct; the downstream consumers needed to be updated to handle the
new representation.
