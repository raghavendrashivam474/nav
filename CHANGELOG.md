# Changelog

All notable changes to NAV are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Planned
- First real AI capability implementation (S3)
- Model provider integration
- Memory persistence layer

---

## [0.1.0-s2] — Sprint 2: Environment & Tooling

### Added
- `pyproject.toml` as single authoritative project configuration
- `ruff` (formatter + linter) as development dependency
- `mypy` (static type checker) as development dependency
- `core/log.py` — centralized logging foundation (stdlib only)
- `tests/test_logging.py` — 4 unit tests for logging
- `.env.example` — environment variable template
- `CONTRIBUTING.md` — contribution guidelines
- `CHANGELOG.md` — this file
- `docs/roadmap.md` — sprint planning and milestones
- `docs/api/contracts.md` — full typed contract reference
- `docs/guides/adding-a-capability.md` — capability walkthrough
- `docs/guides/testing.md` — testing patterns guide
- `docs/s2/completion-report.md` — sprint 2 completion record

### Changed
- Updated `.gitignore` with tooling artifact exclusions (`.mypy_cache/`, `.ruff_cache/`, `*.egg-info/`)
- Updated `README.md` with S2 status and full Quick Start
- Updated `docs/development.md` with complete setup and tooling commands
- Applied Ruff formatting and lint fixes across all S1 source files (style only, no logic changes)
- Modernized type annotations: `typing.Dict` → `dict`, `typing.List` → `list` (Python 3.10+ syntax)

### Fixed
- Import ordering across all modules (Ruff I001)
- Line length violations in `cognition.py` and `orchestrator.py` (Ruff E501)
- Missing trailing newlines (Ruff W292)

### Verified
- All 4 S1 contract tests continue to pass
- 8 total tests passing (4 contracts + 4 logging)
- Mypy: 0 issues across 13 core source files
- Ruff: 0 lint errors, 34 files formatted

---

## [0.1.0-s1] — Sprint 1: Architectural Skeleton

### Added
- Full directory structure representing all architectural boundaries
- `core/contracts/capability.py` — `Capability`, `Request`, `Response`
- `core/contracts/context.py` — `UserContext`, `SessionContext`, `ConversationContext`, `NavContext`
- `core/contracts/ai.py` — `AIGateway`, `AIRequest`, `AIResponse`, `AIMessage`
- `core/contracts/memory.py` — `MemoryCapabilityInterface`, `MemoryRecord`, `MemoryQuery`
- `core/contracts/research.py` — `ResearchCapabilityInterface`, `ResearchQuery`, `ResearchResult`
- `core/capabilities/registry.py` — `CapabilityRegistry`
- `core/orchestration/orchestrator.py` — `Orchestrator`
- `capabilities/cognition/cognition.py` — Cognition verification stub
- `tests/test_contracts.py` — 4 unit tests
- `docs/architecture.md` — full architectural specification
- `docs/development.md` — initial development guide
- `docs/s1/completion-report.md` — sprint 1 completion record
- `README.md` — project overview

### Design Decisions
- Python standard library only (zero external dependencies)
- Frozen dataclasses for all request/response types
- Registry pattern for capability discovery
- Vendor-agnostic abstract interfaces
- Security as first-class boundary