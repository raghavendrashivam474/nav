# Sx1.1 Reconnaissance: Identity & Authority Boundary Baseline

## 1. Overview
Sx1.1 establishes the Aryntra Blackbox security evaluation framework by targeting the Identity -> Authority -> Authorization boundary established in S20.

## 2. Components Under Inspection
- `core/contracts/security.py`: Base frozen dataclass contracts for `ActorIdentity`, `ActorType`, `AuthorizationRequest`, `AuthorizationOutcome`, `AuthorizationDecision`.
- `core/security/policy.py`: `PolicyEngine` evaluating ordered rules with fail-closed (`DENY`) semantics.
- `core/security/service.py`: `SecurityService` orchestrating policy evaluation, event recording, and fallback handling.
- `core/orchestration/orchestrator.py`: Orchestrator capability router acting as the single enforcement boundary.
- `capabilities/work/service.py`: `WorkService` direct lifecycle methods.

## 3. Initial Baseline Invariants
1. `ActorIdentity` is a frozen dataclass distinguishing `USER`, `AGENT`, `SYSTEM`.
2. Policy rules match on actor type, action pattern, and resource pattern, evaluated in priority order.
3. If no policy matches, `PolicyEngine` returns `DENY`.
4. Human approval (S18) is strictly independent of Security authorization (S20). Human approval cannot override a security `DENY`.
