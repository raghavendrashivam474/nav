# ADR-005: Security Plane Architecture and Interim Hardening

## Status
Accepted (S20 Delivered)

## Context
Security must be an independent enforcement plane. In v0.10, prompt
injection defenses exist in `capabilities/research/security.py`,
while `security/` was empty.

## Decision
- S11 documents the target Security Enforcement Plane.
- Full unified security infrastructure was formally scheduled for S20.
- S20 (v1.10) delivers the Identity & Security Plane:
  `core/security/` and `core/contracts/security.py`.
- Interim capability-level defenses (e.g., untrusted content
  delimiters) remain fully valid and active.

## S20 Implementation Summary
- `core/contracts/security.py` — ActorIdentity, AuthorizationRequest,
  AuthorizationDecision, AuthorizationOutcome
- `core/security/policy.py` — Deterministic PolicyEngine with ordered
  rules, fail-closed default
- `core/security/service.py` — SecurityService with event logging
- `core/security/events.py` — SecurityEventLog for observability
- `core/orchestration/orchestrator.py` — Authorization check before
  capability dispatch
- Backward compatibility via SYSTEM_ACTOR default for S17-S19 paths

## Consequences
- Does not prematurely over-engineer security in S11 while ensuring
  no capability treats external data as authority.
- S20 establishes the enforcement boundary at the Orchestrator level,
  independent of AI model, frontend, and individual capabilities.
