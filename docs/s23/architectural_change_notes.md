# S23 Architectural Change Notes

## Decision: Case A — No material architectural change required.

> Existing capability/orchestration/security boundaries are sufficient.
> S23 adds an external information capability within the existing
> capability dispatch pattern.

## What was added (additive only):

1. `core/contracts/external_information.py` — New contract module
2. `capabilities/external_information/` — New capability package
3. `tests/test_s23_external_information.py` — New test module

## What was NOT changed:

- [x] No modifications to `core/orchestration/`
- [x] No modifications to `core/security/`
- [x] No modifications to `core/context/`
- [x] No modifications to existing capabilities
- [x] No modifications to Work, Interaction, or Presence
- [x] No new authorization mechanism
- [x] No new orchestration path

## Compatibility:

- All v1.12 contracts remain unchanged
- New contracts are in a new module (no namespace collision)
- Provider abstraction is self-contained
- S20 security plane remains authoritative

## Future consequences:

- S24 (Evidence/Provenance) will extend `SourceMetadata`
- S24 may add trust/reasoning layers on top of `ExternalInformationResult`
- Future providers (web, API) will implement `ExternalInformationProvider`
- The registry pattern supports multi-provider selection in future sprints
