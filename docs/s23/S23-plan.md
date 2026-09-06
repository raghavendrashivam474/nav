# S23 Plan — External Information Capability

## Objective
Give NAV a legitimate, replaceable capability for acquiring external
information through a stable contract, governed by S20 security.

## Scope
- External information request/response contracts
- Provider abstraction (Protocol)
- One concrete provider (narrow, reliable)
- Integration with existing Orchestrator dispatch
- Integration with existing S20 security plane
- Acquisition-time provenance metadata
- Explicit failure modes (no silent failures, no fake research)

## Out of Scope (deferred to S24+)
- Full evidence/provenance reasoning
- Trust scoring
- Multi-source comparison
- Autonomous research planning
- Vector storage / knowledge graphs

## Constraints
- v1.12 is FROZEN — additive changes only
- No new security architecture
- No new orchestration path
- No new context system
- Provider must be replaceable without touching Core

## Implementation Order
1. Reconnaissance (Phase 1)
2. Contracts (Phase 3)
3. Provider abstraction (Phase 4)
4. Concrete provider (Phase 5)
5. Capability integration (Phase 6)
6. Tests (Phase 7)
7. Documentation (Phase 8)

## Definition of Done
See S23 brief §23.
