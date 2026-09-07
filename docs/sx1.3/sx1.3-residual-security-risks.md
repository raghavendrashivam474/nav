# Sx1.3 Residual Security Risks

**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Date:** 2026-09-08

---

## 1. Purpose

This document records security limitations that remain after Sx1.3.
These are not bugs — they are conscious boundaries of the current
trust model. Recording them explicitly ensures future sprints can
address them with full context.

---

## 2. Residual Risk 1: No Authentication Mechanism

**Severity:** ARCHITECTURAL
**Applicable Threat Model:** Distributed / multi-process deployment

NAV has no `authenticate()`, no credential validation, no session
tokens, no cryptographic identity verification. Identity claims are
treated as identity facts, with sanitization applied to prevent
untrusted input from claiming elevated authority.

### Current Mitigation

Single-process deployment: all code runs in the same trust domain.
Any code that can construct an `ActorIdentity` object is already
inside the trust boundary.

### Future Requirement

When NAV becomes distributed or accepts network requests, an
authentication layer must be introduced. Candidate mechanisms:

- JWT with signed claims
- mTLS with client certificates
- OIDC / OAuth2 integration
- Session tokens with server-side validation

### Detection

- `test_atk10_no_authentication_result_exists`
- `test_atk11_no_auth_means_no_fail_mode`

---

## 3. Residual Risk 2: No Identity Provenance

**Severity:** ARCHITECTURAL
**Applicable Threat Model:** Compromised internal component

The system cannot answer the question "where did this identity come
from?" Once an `ActorIdentity` object exists, it is indistinguishable
from any other identity with the same field values.

### Current Mitigation

Orchestrator boundary sanitization ensures that regardless of
provenance, trust is stripped to 0 for all non-SYSTEM actors.

### Future Requirement

Provenance tracking would require:

- Immutable audit trail of identity construction
- Cryptographic attestation of identity origin
- Session binding with cryptographic proof

### Detection

- `test_atk15_provenance_is_architectural_gap`

---

## 4. Residual Risk 3: SYSTEM_ACTOR Equality-Based Recognition

**Severity:** LOW
**Applicable Threat Model:** In-process code execution

The orchestrator recognizes SYSTEM_ACTOR via `is` OR `==` check.
A forged `ActorIdentity` with matching `actor_id="nav:system"`,
`actor_type=SYSTEM`, `trust_level=100` would pass the equality
check.

### Current Mitigation

The forgery grants no additional authority beyond what SYSTEM_ACTOR
already has. Forgery requires in-process code execution, which
already implies trust boundary compromise.

### Future Requirement

If SYSTEM_ACTOR gains sensitive metadata or per-session context,
consider replacing equality check with a signed token or session ID.

### Detection

- `test_atk13_system_actor_preserved_through_deepcopy`
- `test_atk13_forged_system_is_downgraded`

---

## 5. Residual Risk 4: No Replay Protection

**Severity:** ARCHITECTURAL
**Applicable Threat Model:** Distributed / network-facing deployment

`ActorIdentity` has no expiry, nonce, or session binding. In a
single-process system this is not a risk (no replay surface exists).

### Current Mitigation

Single-process architecture. No message transport where replay could
occur.

### Future Requirement

When network transport is introduced, add:

- Nonce or request-ID tracking
- Timestamp with clock skew tolerance
- Session/token expiry

### Detection

- `test_atk06_identity_has_no_expiry_or_nonce`

---

## 6. Residual Risk 5: Trust Level Persisted for Audit

**Severity:** LOW
**Applicable Threat Model:** Persistence layer tampering

`work.metadata["initiating_actor"]["trust_level"]` stores the
originally-claimed trust level for audit purposes. An attacker with
write access to SQLite could modify this value.

### Current Mitigation

The orchestrator strips trust to 0 on re-entry regardless of stored
value. The persisted value is audit-only and cannot influence
authorization decisions.

### Future Requirement

If persisted trust ever needs to influence authorization, replace
raw storage with signed audit records.

### Detection

- `test_atk08_persisted_trust_is_stripped`

---

## 7. Residual Risk 6: Metadata Not Cryptographically Bound

**Severity:** LOW
**Applicable Threat Model:** In-process metadata substitution

Identity metadata is immutable within a single `ActorIdentity`
instance, but there is no cryptographic binding between the identity
and its metadata. An attacker could construct a new `ActorIdentity`
with different metadata.

### Current Mitigation

Policy engine does not read metadata for authorization decisions.
Metadata is informational only.

### Future Requirement

If metadata becomes authorization-relevant, add signature verification
or move metadata into signed claims.

### Detection

- `test_atk14_metadata_not_used_for_authorization`

---

## 8. Summary

| # | Risk | Severity | Mitigation | Future Sprint |
|---|------|----------|-----------|---------------|
| 1 | No authentication | ARCHITECTURAL | Single-process trust boundary | Sx2+ distributed |
| 2 | No provenance | ARCHITECTURAL | Orchestrator sanitization | Sx2+ distributed |
| 3 | SYSTEM_ACTOR equality check | LOW | No extra authority granted | Only if SYSTEM gains sensitive context |
| 4 | No replay protection | ARCHITECTURAL | No network surface | Sx2+ distributed |
| 5 | Trust persisted for audit | LOW | Orchestrator strips on re-entry | Only if audit becomes authoritative |
| 6 | Metadata not cryptographically bound | LOW | Not used for authorization | Only if policy reads metadata |
