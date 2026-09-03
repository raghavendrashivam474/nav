# NAV — Navigate · Augment · Venture (v0)

NAV is a personal AI system designed around modular capabilities, a hybrid AI routing strategy, and a voice-first interface.

## Core Capabilities (v0)

```text
Cognition — Understand requests, reason, and produce responses.
Memory — Retain and retrieve useful user context.
Research — Discover, retrieve, and synthesize external information.
Sprint Status
 S1 — Project Structure & Architectural Skeleton (Complete)
 S2 — Prerequisites & Environment Verification (Complete)
 S3 — First Real Capability Implementation (Next)
Architecture Overview
NAV follows stable contracts over stable implementations. Core coordinates capabilities through abstract interfaces without vendor lock-in.

Detailed specifications:

Architecture Spec
Development Guide
Quick Start
PowerShell

# Clone and enter the repository
git clone <repo-url>
cd NAV

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install with development dependencies
pip install -e ".[dev]"

# Run the test suite
python -m unittest discover -s tests -v

# Run linting and formatting checks
ruff check .
ruff format --check .

# Run type checking
mypy core/