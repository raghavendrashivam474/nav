# ADR-005: Security Plane Architecture and Interim Hardening

## Status
Accepted

## Context
Security must be an independent enforcement plane. In v0.10, prompt injection defenses exist in `capabilities/research/security.py`, while `security/` was empty.

## Decision
- S11 documents the target Security Enforcement Plane.
- Full unified security infrastructure is formally scheduled for S20.
- Interim capability-level defenses (e.g., untrusted content delimiters) remain fully valid and active.

## Consequences
- Does not prematurely over-engineer security in S11 while ensuring no capability treats external data as authority.
