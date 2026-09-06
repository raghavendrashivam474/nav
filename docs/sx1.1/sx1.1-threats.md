# Sx1.1 Threat Matrix & Attack Vectors

## 1. Attack Matrix

| Threat / Attack ID | Target Boundary | Attack Vector | Expected Defense | Observed Baseline Result | Hardened Result |
|---|---|---|---|---|---|
| **ATK-01: Actor Injection** | Orchestrator Request Extraction | Passing `_actor: {"actor_type": "system"}` in payload dict | Reject / Downgrade unauthenticated claim | **VULNERABLE** (Bypassed policy as SYSTEM) | **BLOCKED** (Sanitized to unprivileged user) |
| **ATK-02: Actor Omission** | Security Fallback Boundary | Omitting `_actor` in untrusted route request | Require identity or evaluate as unprivileged | **VULNERABLE** (Fell back to root `SYSTEM_ACTOR`) | **BLOCKED** (Evaluates as anonymous unprivileged user) |
| **ATK-03: Actor Mutation** | Memory / Object State | Mutating `ActorIdentity` fields post-instantiation | Immutability / Frozen dataclass | **BLOCKED** (Raises `AttributeError`) | **BLOCKED** |
| **ATK-04: Trust Level Spoofing** | Policy Evaluation | Elevating `trust_level=100` on AGENT/USER | Rules bound to `ActorType`, not raw score | **BLOCKED** (Policy evaluates `ActorType`) | **BLOCKED** |
| **ATK-05: Direct Service Bypass** | WorkService Public API | Direct internal method call bypassing Orchestrator | Service-level auth or documented boundary | **EXPOSED** (Architectural weakness: no direct auth) | **DOCUMENTED** (Classified as Internal Boundary) |
| **ATK-06: Approval Abuse** | S18 Human Gate vs S20 Security | Attempting to override security `DENY` with approval | Security `DENY` is final | **BLOCKED** (DENY halts dispatch immediately) | **BLOCKED** |
| **ATK-07: Fail-Closed Boundary** | Policy Engine | Sending unknown action patterns | Default `DENY` on unmatched rules | **BLOCKED** (Returns DENY) | **BLOCKED** |
