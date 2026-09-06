# Sx1.1 Hardening Implementation

## 1. Overview
Sx1.1 hardened the identity and authorization boundaries proven weak by the adversarial test matrix while maintaining full backward compatibility with S17-S25 components.

## 2. Hardening Applied

### 2.1 Orchestrator Actor Extraction & Sanitization (`core/orchestration/orchestrator.py`)
- **Direct Object Preservation:** If `request.payload["_actor"]` is an in-memory `ActorIdentity` instance (constructed by trusted internal subsystems), it is preserved.
- **Untrusted Payload Dictionary Sanitization:** If `_actor` is a raw `dict` (such as from an untrusted caller or serialized JSON payload):
  - Claims of `actor_type == "system"` are downgraded to `ActorType.USER`.
  - The `trust_level` is set to `0`.
  - Unrecognized actor types fallback safely to `ActorType.USER`.
- **Actor Omission Handling:** If `_actor` is omitted or `None`, Orchestrator defaults the request actor to an unprivileged user identity (`actor_id="anonymous", actor_type=ActorType.USER, trust_level=0`) instead of passing `None` (which previously escalated to `SYSTEM_ACTOR`).

### 2.2 Security Invariant Preservation
- `SecurityService.authorize()` retains legacy compatibility for explicit internal unit tests calling `authorize()` without an actor.
- Human approval (S18) remain strictly isolated from security authorization (S20).
- `PolicyEngine` remains purely deterministic, evaluating rules in priority order and failing closed (`DENY`).
