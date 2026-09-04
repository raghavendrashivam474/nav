# S11 Architectural Change Note: v1 Foundation & Context Manager Contract

## Observed Problem
1. **Empty Context Coordination Package**: `core/contracts/context.py` defines `NavContext`, `UserContext`, and `SessionContext`, but `core/context/__init__.py` was an empty package with no coordination contract.
2. **Deep Import Friction**: `core/contracts/__init__.py` contained no re-exports, requiring deep import paths for standard contracts across all tests and capabilities.
3. **Redundant Package Stub**: An empty `ai/router/` directory existed alongside the active `ai/routing/` package.
4. **Interface vs. Capability Ambiguity**: The role of Voice relative to NAV Core needed formal architectural stabilization before external systems (Avni) integrate.

## Evidence
- Baseline reconnaissance identified `core/context/__init__.py` as 0 bytes.
- Audit documented 10 strengths (KEEP), 12 debts (IMPROVE/DEFER), and 4 research decisions (ADR-001 through ADR-005).

## Existing Components Responsible
- `core/contracts/context.py`: Defines context dataclasses.
- `core/contracts/`: Holds subsystem contracts.
- `ai/routing/`: Implements policy-driven model routing.
- `interfaces/voice/`: Coordinates audio ingress/egress.

## Architectural Changes Made in S11

### 1. ContextManager Abstract Contract (`core/context/context_manager.py`)
Introduced abstract base class `ContextManager` defining the core API for assembling `NavContext` snapshots and managing user, session, and conversation context lifecycle without coupling Core to persistent database engines.

### 2. Core Contracts Package Re-exports (`core/contracts/__init__.py`)
Added clean, top-level re-exports for all core capability contracts, AI contracts, memory interfaces, context data models, and research protocols.

### 3. Redundant Package Pruning
Removed unused empty directory `ai/router/` to prevent developer confusion with active `ai/routing/`.

### 4. Architectural Specifications & ADRs
- Published `docs/architecture/v1-architecture.md` (North Star architecture baseline).
- Published `docs/architecture/external-integration.md` (Adapter/Provider model for Avni and external systems).
- Published `ADR-001` through `ADR-005` in `docs/architecture/decisions/`.

## Alternatives Considered & Rejected
- **Alternative A: Convert Voice into a Capability registered in Core.**
  - *Rejected (ADR-001)*: Voice is an interaction interface that produces standard `Request`/`Response` objects. Converting it into a capability would turn the orchestrator into an audio processor.
- **Alternative B: Move `capabilities/research/context_store.py` into `core/context/`.**
  - *Rejected*: Research context is domain-specific volatile state. Core owns the general `ContextManager` contract; capability-specific stores remain within their capability boundaries.

## Backward Compatibility
100% preserved. All existing v0.10 capabilities, interfaces, and test suites run without modification.

## Verification
- 246 tests passing (`pytest`).
- Clean Ruff lint and format check.
- Clean Mypy check across 99 files.