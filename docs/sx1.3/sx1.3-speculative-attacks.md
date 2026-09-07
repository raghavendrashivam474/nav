# Sx1.3 Speculative Attacks (Future Threat Landscape)

**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Date:** 2026-09-08

---

## 1. Purpose

This document catalogs attack scenarios that are NOT currently
applicable to NAV but would become viable under future architectural
changes. These are recorded to inform future sprint planning.

**These are not current vulnerabilities.** They are attack scenarios
that must be considered when the architecture evolves.

---

## 2. Speculative Attack 1: Network Identity Injection

**Trigger:** NAV gains a network-facing API (REST, gRPC, WebSocket)

### Scenario

An external attacker submits a request with a forged actor payload.
Without authentication, the orchestrator's sanitization would still
strip trust to 0, but the attacker could impersonate any user_id.

### Impact

- Audit logs contain attacker-chosen user identities.
- Rate limiting or user-scoped policies could be bypassed.
- Denial of service against specific users.

### Required Mitigation

- Authentication layer at network boundary.
- Cryptographic user identity verification.

---

## 3. Speculative Attack 2: Distributed Session Hijacking

**Trigger:** NAV becomes multi-process or multi-node

### Scenario

An attacker intercepts or steals a session identifier and replays it
against a different NAV instance. With no session binding to the
originating process/node, the replay succeeds.

### Impact

- Full user impersonation across nodes.
- Bypass of per-node access controls.

### Required Mitigation

- Session tokens with server-side validation.
- Node-bound or time-bound session identifiers.
- Nonce or request-ID tracking.

---

## 4. Speculative Attack 3: Serialization Deserialization Chain

**Trigger:** Work metadata is exchanged between untrusted parties

### Scenario

If NAV work items are exported/imported across trust boundaries, an
attacker could craft malicious metadata that exploits deserialization
paths. The current code uses JSON (safe from pickle-style RCE) but
could be affected by future changes to binary serialization.

### Impact

- Depending on serialization format: RCE, DoS, or data corruption.

### Required Mitigation

- Stay on JSON serialization (never pickle for cross-trust data).
- Schema validation on deserialization.
- Signed serialization envelopes for cross-trust exchange.

---

## 5. Speculative Attack 4: Metadata-Based Policy Exploitation

**Trigger:** Policy engine gains rules that read `ActorIdentity.metadata`

### Scenario

If a future policy rule reads `metadata["role"]` or similar for
authorization decisions, an attacker could construct an
`ActorIdentity` with attacker-chosen metadata to gain authority.

### Impact

- Authorization bypass through metadata injection.

### Required Mitigation

- Do not use metadata for authorization decisions (current design).
- If metadata must be authoritative, add cryptographic signing.

### Detection

- Code review: grep for `metadata.get(` in policy code.
- `test_atk14_metadata_not_used_for_authorization` regression.

---

## 6. Speculative Attack 5: SYSTEM_ACTOR Field Cloning

**Trigger:** SYSTEM_ACTOR gains additional fields (e.g., session context)

### Scenario

If SYSTEM_ACTOR is extended with fields like `session_id` or
`execution_context`, and an attacker constructs an `ActorIdentity`
with matching `actor_id`, `actor_type`, `trust_level` (which
passes the current equality check), the attacker gains access to
whatever the new fields grant.

### Impact

- Elevation to SYSTEM authority with attacker-controlled context.

### Required Mitigation

- Replace equality check with signed session token.
- Or: keep SYSTEM_ACTOR minimal and pass session context separately.

---

## 7. Speculative Attack 6: MappingProxyType Bypass via C Extension

**Trigger:** New C extension or ctypes usage in NAV

### Scenario

`MappingProxyType` prevents Python-level mutation but the underlying
dict can be modified via ctypes or a C extension that accesses the
raw dict pointer.

### Impact

- Metadata mutation despite immutability guarantee.

### Required Mitigation

- Do not use ctypes/C extensions on identity objects.
- If required: use `frozendict` or copy-on-access patterns.

---

## 8. Speculative Attack 7: Time-of-Check to Time-of-Use on Reload

**Trigger:** Long-running work items with delayed step execution

### Scenario

An actor is authorized at work creation time. The work runs for
hours. During execution, the actor's privileges are revoked (in a
future system with credential revocation). The stored
`initiating_actor` in work metadata still reflects the original
trust.

### Impact

- Revoked credentials continue to execute privileged operations.

### Required Mitigation

- Re-authorize at each step execution (not just work creation).
- Support credential revocation with propagation to running work.
- Or: short-lived authorization tokens with refresh.

---

## 9. Speculative Attack 8: Cross-Sprint Assumption Leakage

**Trigger:** Future sprint introduces new identity consumer

### Scenario

A new capability or service reads `ActorIdentity.metadata` or
`trust_level` under the assumption that it reflects verified state.
Because current metadata is not cryptographically bound and trust is
sanitized at the orchestrator (not the identity itself), the
consumer trusts data that has not been verified.

### Impact

- Authorization bypass in the new consumer.

### Required Mitigation

- Code review checklist: identity fields are informational only.
- Add architectural test: policy engine + all authorization decision
  points must only read `actor_type` after orchestrator sanitization.

---

## 10. Summary Matrix

| # | Attack | Trigger | Severity if Triggered |
|---|--------|---------|----------------------|
| 1 | Network identity injection | Network API added | HIGH |
| 2 | Distributed session hijacking | Multi-node deployment | HIGH |
| 3 | Serialization deserialization chain | Cross-trust data exchange | CRITICAL |
| 4 | Metadata-based policy exploitation | Policy reads metadata | HIGH |
| 5 | SYSTEM_ACTOR field cloning | SYSTEM_ACTOR extended | HIGH |
| 6 | MappingProxyType C bypass | C extension added | MEDIUM |
| 7 | TOCTOU on reload | Credential revocation added | MEDIUM |
| 8 | Cross-sprint assumption leakage | New identity consumer | MEDIUM |
