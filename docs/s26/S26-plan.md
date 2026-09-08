
S26 Sprint Plan — Comparison & Comparative Intelligence
Sprint: S26
Baseline: NAV v2.2 (Tag vx1.f)

1. Objectives
Define comparison contracts in core/contracts/comparison.py and re-export in core/contracts/__init__.py.
Implement deterministic & model-assisted Comparison Engine in capabilities/comparison/engine.py.
Implement ComparisonService facade in capabilities/comparison/service.py.
Implement Orchestrator-facing ComparisonCapability in capabilities/comparison/capability.py.
Comprehensive unit, deterministic, evidence-aware, model-assisted, integration, and adversarial tests in tests/test_s26_*.
Full documentation (contracts, architecture, ADR 0016, implementation & completion reports).
2. Deliverables Matrix
Component    File Path    Scope
Comparison Contracts    core/contracts/comparison.py    Data structures for subjects, dimensions, evaluations, relationships, and comparison results
Contract Re-export    core/contracts/__init__.py    Add comparison types to __all__
Comparison Engine    capabilities/comparison/engine.py    Deterministic & model-assisted comparative evaluations
Comparison Service    capabilities/comparison/service.py    Subsystem facade integrating Evidence and Synthesis
Comparison Capability    capabilities/comparison/capability.py    Capability interface implementation for Orchestrator dispatch
Package Init    capabilities/comparison/__init__.py    Expose facade and capability
ADR 0016    docs/architecture/decisions/0016-s26-comparison-capability.md    Architectural record of comparison foundation
Test Suite    tests/test_s26_*.py    Contract, engine, capability, and adversarial tests
Docs    docs/s26/*.md    Recon, specs, architecture, implementation, completion
