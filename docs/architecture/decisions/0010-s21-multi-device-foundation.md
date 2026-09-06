# ADR 0010: S21 Multi-device Foundation

## Status
Accepted

## Context
NAV v1.10 operates as a single-runtime system. All state (context, memory,
work, investigations) is implicitly local to one process on one device.
The v2 North Star envisions a persistent personal intelligence environment
that travels across devices. S21 must establish the architectural foundation
for this transition without prematurely building distributed infrastructure.

## Decision
Introduce three identity layers as frozen dataclass contracts:

1. **EnvironmentIdentity** — the logical personal NAV environment (durable)
2. **DeviceIdentity** — a physical/logical host (durable across restarts)
3. **RuntimeIdentity** — a specific process instance (ephemeral)

Plus supporting contracts:
- **DeviceCapabilities** — descriptive boolean capability flags
- **RuntimeDescriptor** — runtime + device composition
- **StateOrigin** — provenance metadata for future sync

A **RuntimeRegistry** provides in-memory runtime membership tracking.

### Key constraints:
- All contracts are `frozen=True` (matching S17-S20 convention)
- Identity does NOT imply authentication or authorization
- S20 SecurityService remains the sole authorization authority
- No networking, synchronization, or cloud dependencies
- No modification to NavContext, Orchestrator, Work, or Interaction
- DEFAULT_ENVIRONMENT constant for backward compatibility (mirrors SYSTEM_ACTOR)

### What this is NOT:
- Not a distributed database
- Not a sync engine
- Not an authentication system
- Not a device management platform

## Consequences
- Future sprints can reference environment/device/runtime identity
- State can be tagged with origin for eventual synchronization
- Capability dispatch can become device-aware without redesign
- No breaking changes to S17-S20 contracts or behavior
