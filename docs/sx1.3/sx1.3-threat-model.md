# Sx1.3 Threat Model

**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Date:** 2026-09-08
**Model Type:** In-process adversarial (no network boundary)

---

## 1. System Boundary

NAV is a single-process Python application. The threat model considers
an adversary who can:

- Construct arbitrary Python objects in-process
- Submit requests through the Orchestrator
- Interact with the Work subsystem
- Read/write the SQLite persistence layer (via NAV APIs)
- Observe security decisions and error messages

The threat model does NOT currently consider:

- Network-level attackers (no remote transport exists)
- Multi-process or distributed deployment
- Compromised Python runtime or OS-level attacks
- Supply chain attacks on dependencies

## 2. Assets

| Asset | Sensitivity | Location |
|-------|-------------|----------|
| Actor identity (who is acting) | HIGH | `ActorIdentity` objects, `work.metadata` |
| Trust level (privilege indicator) | HIGH | `ActorIdentity.trust_level` |
| Actor type (role classification) | HIGH | `ActorIdentity.actor_type` |
| SYSTEM authority | CRITICAL | `SYSTEM_ACTOR` singleton |
| Authorization decisions | HIGH | `SecurityService` / `PolicyEngine` |
| Work execution context | MEDIUM | `Work.metadata`, `WorkStep` |
| Identity metadata | MEDIUM | `ActorIdentity.metadata` |

## 3. Threat Actors

| Actor | Capability | Motivation |
|-------|-----------|------------|
| In-process caller | Can construct arbitrary `ActorIdentity` objects | Privilege escalation |
| Payload injector | Can supply arbitrary `_actor` dicts in requests | Identity spoofing |
| Persistence manipulator | Can modify stored work metadata | Authority fabrication |
| Metadata mutator | Can modify `ActorIdentity.metadata` after creation | Signal injection |

## 4. Attack Surface

### 4.1 Identity Claim Injection
An attacker constructs an `ActorIdentity` with `actor_type=SYSTEM`
and `trust_level=100`, passing it as `_actor` in a request payload.
Pre-Sx1.3, the orchestrator's `isinstance` bypass accepted this
without validation.

### 4.2 Trust Level Inflation
An attacker sets `trust_level=999` on an `ActorIdentity` object.
Pre-Sx1.3, the orchestrator preserved this value for object-based
actors.

### 4.3 Metadata Tampering
An attacker modifies `identity.metadata["admin"] = True` after
identity creation. Pre-Sx1.3, the frozen dataclass prevented field
reassignment but not dict mutation.

### 4.4 Serialization Forgery
An attacker manipulates the serialized form of an identity in SQLite
to restore elevated trust on deserialization.

### 4.5 Cross-Request Identity Confusion
An attacker exploits shared mutable state (metadata dict references)
to leak identity information between requests.

### 4.6 SYSTEM Identity Forgery
An attacker constructs a fake `SYSTEM_ACTOR` equivalent and attempts
to gain system-level authorization.

## 5. Trust Model (Post-Sx1.3)

The current trust model is **in-process construction trust**:

- `SYSTEM_ACTOR` is trusted because it is a module-level constant
  constructed by the runtime, not by external input.
- All other identities are treated as untrusted claims.
- The orchestrator strips trust to 0 for all non-SYSTEM actors.
- Trust cannot be elevated through persistence or metadata.
- There is no cryptographic verification, credential checking, or
  external authentication authority.

This is a **sanitization model**, not an **authentication model**.
The system prevents untrusted input from becoming trusted authority,
but it does not independently verify that any actor is who they claim
to be (except for the in-process `SYSTEM_ACTOR` constant).

## 6. Security Goals

| Goal | Status | Mechanism |
|------|--------|-----------|
| Untrusted input cannot become trusted authority | ACHIEVED | Orchestrator sanitization |
| Identity fields cannot be mutated post-creation | ACHIEVED | Frozen dataclass + MappingProxyType |
| Persistence cannot manufacture authority | ACHIEVED | Trust stripped on reload |
| SYSTEM authority cannot be forged | ACHIEVED | Equality check against singleton |
| Cross-request identity isolation | ACHIEVED | Deep copy + immutable metadata |
| Cryptographic identity verification | NOT ACHIEVED | No mechanism exists |
| External authentication | NOT ACHIEVED | No mechanism exists |
| Identity provenance tracking | NOT ACHIEVED | Documented as architectural gap |
