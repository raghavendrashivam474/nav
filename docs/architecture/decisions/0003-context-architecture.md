# ADR-003: Context Architecture and ContextManager Contract

## Status
Accepted

## Context
`core/context/` was an empty package in v0.10 despite the existence of rich context contracts in `core/contracts/context.py`. Multi-turn research state was managed locally within `capabilities/research/context_store.py`.

## Decision
Establish the `ContextManager` abstract contract in `core/context/context_manager.py`.
- `NavContext` remains the top-level immutable snapshot.
- `ContextManager` defines the contract for resolving, attaching, and tracking session and user context across capabilities.
- Capability-specific volatile stores (like `ResearchContextStore`) retain ownership of their domain state while conforming to the context model.

## Consequences
- Lays the clean architectural contract for personal context in S12+ without breaking existing S10 research continuity.
