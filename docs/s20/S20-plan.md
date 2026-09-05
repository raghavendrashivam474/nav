# S20 Sprint Plan — Identity & Security Plane

**Target Release:** v1.10
**Sprint:** S20
**Status:** Complete
**Previous Baseline:** S19 / v1.9

## Mission

Establish the first real Identity & Security Plane for NAV.

> Who is allowed to make NAV do what, under which authority, and how
> does NAV enforce that boundary independently of the AI/model and
> individual capabilities?

## Architectural Relationship
```text
User / Actor
↓
Identity
↓
Authentication / Trust
↓
Authorization / Policy
↓
Human Control / Approval
↓
Capability
↓
Execution
```


## Deliverables

| File | Purpose |
|------|---------|
| `core/contracts/security.py` | Identity & authorization contracts |
| `core/security/policy.py` | Deterministic policy engine |
| `core/security/service.py` | Central authorization service |
| `core/security/events.py` | Security event log |
| `core/orchestration/orchestrator.py` | Security enforcement at dispatch |
| `tests/test_s20_security.py` | 43 tests, all 7 invariants |
| ADR-005 | Updated with S20 delivery |
| ADR-009 | Enforcement architecture decisions |
