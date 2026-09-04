# ADR-002: Runtime Boundary Definition and Bootstrap Model

## Status
Accepted

## Context
Investigate the distinction between NAV Core and NAV Runtime.

## Decision
NAV Core is defined strictly as contracts, registration, and stateless coordination (`core/`).
The Runtime layer represents the concrete wiring, lifecycle management, and environment bootstrap.
For S11, the runtime bootstrap pattern is formalized without introducing unnecessary packaging overhead.

## Consequences
- Core remains completely free from I/O, database initialization, and environment variable parsing.
- Capabilities and providers remain fully testable in isolation without running a full daemon.
