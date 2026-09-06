# S21 Implementation Plan

## Phase 1-3: Recon + Baseline + Architecture Decision ✅
Completed. See S21-recon-notes.md and baseline.md.
ADR: 0010-s21-multi-device-foundation.md

## Phase 4: Contracts
- core/contracts/environment.py
  - EnvironmentIdentity, DeviceIdentity, RuntimeIdentity
  - DeviceCapabilities, DevicePlatform, RuntimeStatus
  - RuntimeDescriptor, StateOrigin
  - DEFAULT_ENVIRONMENT constant (mirrors SYSTEM_ACTOR pattern)

## Phase 5: Runtime/Environment Foundation
- core/environment/identity.py (generation helpers)
- core/environment/registry.py (RuntimeRegistry, in-memory)
- core/environment/__init__.py

## Phase 6: State Boundary
- StateOrigin contract (in Phase 4) provides the metadata.
- No modification to existing repositories (additive only).

## Phase 7: Security Integration
- Verify env identity does NOT bypass S20.
- No policy changes. No new authorization paths.

## Phase 8: Tests
- tests/test_s21_environment.py

## Phase 9: Documentation
- ADR 0010, implementation notes, completion report.

## Phase 10: Release Verification
- pytest, ruff, mypy, git tag v1.11
