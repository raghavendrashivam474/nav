# Sx1.4 Service & Execution Boundary Hardening

## Hardening Review & Verifications

### 1. Unified Locus of Authorization
Authorization enforcement remains strictly centralized at `Orchestrator.route_request()`.
This ensures:
- Single source of policy truth (`core/security/policy.py`).
- Single audit point for security events (`core/security/events.py`).
- Deterministic behavior without layer-to-layer policy discrepancies.

### 2. Adversarial Test Coverage
Added 45 new adversarial test cases across:
- `tests/test_sx1_4_service_boundary.py` (30 tests: ATK-01 to ATK-08)
- `tests/test_sx1_4_context_attacks.py` (15 tests: ATK-09 to ATK-15)

All 45 tests verify both the positive security enforcement when routed through the Orchestrator and document the boundary behavior of direct internal calls.
