# S20 Architectural Change Notes

## Changes Made

### 1. Orchestrator Constructor
Added optional `security_service: SecurityService | None = None`
parameter. Fully backward compatible — defaults to `None`, no
security check when absent.

### 2. Request Payload Convention
Introduced `_actor` key for passing identity through the frozen
`Request` dataclass. This is a convention, not a contract change.
The Orchestrator extracts and evaluates it before dispatch.

## Changes NOT Made

| Component | Status |
|-----------|--------|
| `Capability` ABC | Untouched |
| `Request` / `Response` dataclasses | Untouched |
| `WorkService` | Untouched |
| `WorkCapability` | Untouched |
| `CapabilityRegistry` | Untouched |
| All S17-S19 code | Untouched |

## Known Limitations

- Direct `WorkService` calls (bypassing Orchestrator) are not yet
  protected by the security plane. This is acceptable for S20 as the
  Orchestrator is the primary dispatch path. Future sprints may add
  service-level enforcement.
