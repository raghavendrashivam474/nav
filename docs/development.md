# NAV Developer Guide

## Development Setup

1. **Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
Dependencies:
Bash

pip install -e ".[dev,voice]"
Running Tests and Quality Checks
Bash

# Run complete test suite
python -m pytest -v

# Run linter
ruff check .

# Run type checker
mypy .
Running Demonstrations
Bash

# S6 Memory Demo
python demo_s6.py

# S7 Research Demo
python demo_s7.py

# S8 Integration & Progressive Interaction Demo
python demo_s8.py
Architectural Invariants (S8)
Core does not know research implementation details.
Research does not know which AI provider is being used.
Research does not know which interface is displaying progress.
Memory remains replaceable and optional.
Voice remains a communication interface.
External content is never treated as NAV authority.
Research concurrency is strictly bounded.
One failed source cannot invalidate successful independent sources.
All S1–S7 behavior remains regression-tested.
Stable contracts remain more important than stable implementations.
