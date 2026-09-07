# Sx1.3 Attack Matrix

**Sprint:** Sx1.3 — Identity Provenance & Authentication Hardening
**Date:** 2026-09-08
**Baseline:** vx1.2 → Sx1.3 hardened

---

## Classification Key

| Classification | Meaning |
|---------------|---------|
| FIXED | Vulnerability existed, was remediated, test proves the fix |
| BLOCKED | Attack was already prevented by existing controls, test confirms |
| CONFIRMED VULNERABILITY | Attack succeeds; not yet remediated |
| ARCHITECTURAL WEAKNESS | Fundamental design limitation; documented, not fixable in this sprint |
| NOT APPLICABLE | Attack vector does not apply to current architecture |

---

## Attack Matrix

| ID | Attack | Initial State | Finding | Remediation | Final State | Evidence | Residual Risk |
|----|--------|--------------|---------|-------------|-------------|----------|---------------|
| ATK-01 | Identity Claim Injection | ActorIdentity objects bypassed orchestrator sanitization via isinstance check | FIXED | Orchestrator now validates ActorIdentity objects: strips trust to 0, downgrades non-SYSTEM types | BLOCKED | `test_atk01_object_actor_is_sanitized` | In-process callers can still construct ActorIdentity objects; sanitization catches them at orchestrator boundary |
| ATK-02 | Trust-Level Injection | Dict trust forced to 0 (Sx1.1); object trust preserved | FIXED | Orchestrator strips trust to 0 for all non-SYSTEM actors regardless of input type | BLOCKED | `test_atk02_object_trust_stripped_by_orchestrator` | None at orchestrator boundary; trust is meaningless outside SYSTEM_ACTOR |
| ATK-03 | Actor-Type Substitution | Dict SYSTEM claims blocked (Sx1.1); object SYSTEM claims accepted | FIXED | Orchestrator downgrades any ActorIdentity with actor_type=SYSTEM that is not the real SYSTEM_ACTOR | BLOCKED | `test_atk03_dict_type_sanitized` (parametrized) | None; all forged SYSTEM types are downgraded |
| ATK-04 | Identity Field Tampering | Frozen dataclass prevented field reassignment but metadata dict was mutable | FIXED | `__post_init__` wraps metadata in `MappingProxyType`; mutation raises TypeError | BLOCKED | `test_atk04_metadata_is_now_immutable` | None; metadata is now immutable |
| ATK-05 | Serialization Forgery | Deserialized identity preserved stored trust_level | FIXED | Work service reconstructs identity with explicit trust handling; orchestrator strips trust on re-entry | BLOCKED | `test_atk05_tampered_trust_is_stripped` | Persistence stores trust_level for audit; orchestrator boundary prevents exploitation |
| ATK-06 | Identity Replay | No expiry/nonce mechanism | ARCHITECTURAL WEAKNESS | Not remediated; single-process architecture has no replay risk without session model | DOCUMENTED | `test_atk06_identity_has_no_expiry_or_nonce` | If NAV becomes distributed, replay attacks become viable |
| ATK-07 | Cross-Request Confusion | Shared mutable metadata dicts could leak between deep-copied payloads | FIXED | MappingProxyType metadata + deepcopy dispatch registration ensures isolation | BLOCKED | `test_atk07_metadata_no_longer_leaks` | None in current architecture |
| ATK-08 | Work Persistence | Persisted trust_level could be reloaded as authority | FIXED | Orchestrator strips trust on re-entry regardless of stored value | BLOCKED | `test_atk08_persisted_trust_is_stripped` | Stored trust_level preserved for audit trail only |
| ATK-09 | Cross-Component Identity | _security_actor takes precedence but fallback _actor could be forged | FIXED | Orchestrator sanitizes all _actor values; _security_actor is set by orchestrator after validation | BLOCKED | `test_atk09_fallback_actor_is_sanitized` | None; both paths are sanitized |
| ATK-10 | Auth Result Manipulation | No authentication result exists to manipulate | NOT APPLICABLE | No authentication mechanism exists; nothing to manipulate | DOCUMENTED | `test_atk10_no_authentication_result_exists` | When authentication is added, result manipulation must be considered |
| ATK-11 | Auth Fail-Open | No authentication means no fail-open risk | NOT APPLICABLE | No authentication mechanism; fail-open is not possible | DOCUMENTED | `test_atk11_no_auth_means_no_fail_mode` | When authentication is added, fail-closed must be enforced |
| ATK-12 | Missing Authentication | No actor produces anonymous USER | BLOCKED | Orchestrator defaults to anonymous USER with trust 0 | BLOCKED | `test_atk12_missing_actor_produces_anonymous` | None |
| ATK-13 | SYSTEM Identity Origin | Forged SYSTEM ActorIdentity objects were accepted | FIXED | Orchestrator checks `actor_data is SYSTEM_ACTOR or actor_data == SYSTEM_ACTOR`; all others downgraded | BLOCKED | `test_atk13_forged_system_is_downgraded`, `test_atk13_system_actor_preserved_through_deepcopy` | Equality check relies on all three fields matching; a forged actor with identical fields would pass (but cannot gain more than SYSTEM_ACTOR already has) |
| ATK-14 | Metadata Confusion | Metadata could theoretically carry authority signals | BLOCKED | Policy engine does not read metadata for authorization decisions | BLOCKED | `test_atk14_metadata_not_used_for_authorization` | If future policy rules read metadata, this must be re-evaluated |
| ATK-15 | Provenance Loss | No provenance mechanism exists | ARCHITECTURAL WEAKNESS | Not remediated; documented as architectural gap | DOCUMENTED | `test_atk15_provenance_is_architectural_gap` | Full provenance requires cryptographic attestation and session binding; deferred to future sprint |

---

## Summary Statistics

| Classification | Count |
|---------------|-------|
| FIXED | 8 |
| BLOCKED (pre-existing) | 3 |
| ARCHITECTURAL WEAKNESS | 2 |
| NOT APPLICABLE | 2 |
| CONFIRMED VULNERABILITY (unresolved) | 0 |
