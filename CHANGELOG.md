# Changelog

## [0.6.0] - Sprint S6 (Persistent Memory)

### Added
- `capabilities/memory/repository.py`: Storage-agnostic `MemoryRepository` abstract base class.
- `capabilities/memory/sqlite_repo.py`: SQLite standard library repository implementation with automatic schema initialization.
- `capabilities/memory/service.py`: `MemoryService` with intent detection (`is_memory_request`, `is_forget_request`).
- `capabilities/memory/capability.py`: Registered `MemoryCapability` implementing both `Capability` and `MemoryCapabilityInterface`.
- `capabilities/cognition/cognition.py`: Integrated optional memory context injection and explicit remember/forget handling.
- `tests/test_memory.py`: 29 tests covering CRUD, query filtering, metadata preservation, and cross-process persistence.
- `tests/test_cognition_memory.py`: 5 tests verifying Cognition-Memory interactions and error isolation.
- `demo_s6.py`: Standalone multi-session demonstration.

### Changed
- `core/contracts/memory.py`: Extended `MemoryCapabilityInterface` with `update()` and `forget()` methods.
- `docs/architecture.md`, `docs/roadmap.md`, `docs/api/contracts.md`: Updated to document S6 deliverables and invariants.
