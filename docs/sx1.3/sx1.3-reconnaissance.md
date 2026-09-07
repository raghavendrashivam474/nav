# Sx1.3 Reconnaissance Report

**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Date:** 2026-09-08
**Baseline:** vx1.2 (commit 819cf86)
**Author:** Blackbox Audit (post-implementation reconstruction)


## 1. Scope

Sx1.3 investigates whether NAV can reliably distinguish a genuinely
trusted actor from one that merely claims to be trusted. The sprint
focuses on the identity lifecycle from creation through serialization,
persistence, deserialization, and cross-component propagation.

## 2. Pre-Sx1.3 Identity Architecture (vx1.2 Baseline)

### 2.1 ActorIdentity Contract

Defined in `core/contracts/security.py` as a frozen dataclass:

```python
@dataclass(frozen=True)
class ActorIdentity:
    actor_id: str
    actor_type: ActorType = ActorType.USER
    trust_level: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
```

Key observation: the dataclass is frozen (fields cannot be reassigned),
but metadata is a mutable dict. Freezing prevents
    identity.trust_level = 100 but does NOT prevent
    identity.metadata["admin"] = True.

### 2.2 SYSTEM_ACTOR Constant
```Python
SYSTEM_ACTOR = ActorIdentity(
    actor_id="nav:system",
    actor_type=ActorType.SYSTEM,
    trust_level=100,
)
```
A module-level singleton. Trust level 100 is hardcoded. No external
authority issues or validates this trust.

### 2.3 Orchestrator Sanitization (Sx1.1)

The orchestrator (core/orchestration/orchestrator.py) performs
actor extraction and sanitization at the dispatch boundary:

- Dict-based actors: actor_type="system" is downgraded to
  USER. Trust is forced to 0.

- ActorIdentity objects: Passed through directly with no
  validation (the isinstance bypass at L49).

- Missing actors: Default to anonymous USER, trust 0.

### 2.4 Work Persistence Path

WorkService.create_work() stores the initiating actor as a
plain dict inside work.metadata["initiating_actor"]. The SQLite
repository serializes this via json.dumps() and deserializes via
json.loads(). On reload, _invoke_capability() reconstructs
an ActorIdentity from the stored dict, preserving the stored
trust_level.

### 2.5 Authentication

There is no authentication mechanism. No authenticate(),
 verify_identity(), check_token(), or equivalent exists
anywhere in the codebase. Identity claims are treated as identity
facts. The orchestrator performs input sanitization, not
authentication.

3. Identity Entry Points Identified
#    Entry Point    Location    Trust Treatment (pre-Sx1.3)
1    payload["_actor"] as dict    Orchestrator L52-65    Sanitized: type/trust stripped
2    payload["_actor"] as ActorIdentity    Orchestrator L49    Unsanitized passthrough
3    work.metadata["initiating_actor"]    WorkService L329-337    Reconstructed with stored trust
4    payload["_security_actor"]    WorkCapability L96    Takes precedence over _actor
4. Identity Persistence Paths
#    Path    Serialization    Deserialization
1    Work metadata → SQLite    json.dumps() via _work_to_data_blob()    json.loads() via _data_blob_to_fields()
2    ActorIdentity → dict    Manual field extraction in create_work()    Manual reconstruction in _invoke_capability()
5. Initial Vulnerability Hypotheses
ActorIdentity object bypass (HIGH): The orchestrator's
isinstance check at L49 accepts any ActorIdentity object
without validation. An in-process caller can construct
ActorIdentity(actor_type=SYSTEM, trust_level=100) and bypass
all sanitization.

Mutable metadata in frozen dataclass (MEDIUM): The metadata
dict can be mutated after creation, potentially injecting authority
signals that downstream consumers might trust.

Trust restoration from persistence (MEDIUM): Work reload
reconstructs identity with the stored trust_level, meaning
persistence can manufacture authority.

No provenance model (ARCHITECTURAL): The system has no concept
of where an identity came from or whether it was independently
verified.

6. Reconnaissance Conclusion
The pre-Sx1.3 architecture provides basic input sanitization for
dict-based actor claims (Sx1.1) and execution boundary enforcement
(Sx1.2), but has three significant gaps:

Object-based identity claims bypass sanitization entirely.
Identity metadata is mutable despite the frozen dataclass.
No authentication or provenance mechanism exists.
Sx1.3 addresses gaps 1 and 2 through implementation hardening.
Gap 3 is documented as an architectural limitation.
