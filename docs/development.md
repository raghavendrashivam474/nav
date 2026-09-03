# NAV Development Guide

## Prerequisites
- Python 3.10 or higher
- Git

## Getting Started
No external dependencies are required for Sprint 1. NAV contracts are built using Python's standard library.

`ash
# Verify directory structure
Get-ChildItem

# Run the test suite
python -m unittest discover -s tests -v
Running Specific Tests
Bash

python -m unittest tests.test_contracts -v
Development Conventions
Contracts First: Any new capability must implement the base Capability interface from core.contracts.capability.
Zero Vendor Leakage in Core: core/ must never import specific vendor packages (e.g., openai, anthropic, psycopg2).
Registry Pattern: Capabilities register with CapabilityRegistry and are invoked via Orchestrator.
Git Hygiene: Never commit keys, .env files, databases, or .pyc caches.
Adding a Capability
Create capabilities/<capability_name>/.
Subclass core.contracts.capability.Capability.
Implement name, version, description, and invoke(request).
Add corresponding tests under tests/.
