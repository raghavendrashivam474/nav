# Contributing to NAV

Thank you for your interest in contributing to NAV (Navigate · Augment · Venture).

## Development Setup

Follow the [Development Guide](docs/development.md) to set up your local environment.

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable, reviewed, sprint-complete code |
| `sprint/s<N>` | Active sprint work (e.g., `sprint/s3`) |
| `feature/<name>` | Isolated feature experiments (rare in v0) |
| `hotfix/<name>` | Urgent fixes to `main` |

### Workflow

1. Create a sprint branch from `main`:
   ```powershell
   git checkout -b sprint/s3
Commit frequently with clear messages.
Run the full verification suite before pushing:
PowerShell

ruff check .
ruff format --check .
mypy core/
python -m unittest discover -s tests -v
Push and open a Pull Request to main.
Require at least one review before merging.
Commit Message Convention
Use a simplified conventional commit format:

text

<type>(<scope>): <short description>

<optional longer body>
Types:

feat — New capability or feature
fix — Bug fix
docs — Documentation only
style — Formatting, no logic change
refactor — Code restructuring, no behavior change
test — Adding or updating tests
chore — Build, tooling, or dependency changes
Examples:

text

feat(s3): implement OpenAI cognition provider
docs(s2): add completion report
style(core): apply ruff formatting to contracts
test(logging): add handler verification tests
Coding Standards
Python
Minimum version: Python 3.10
Formatter: Ruff (run ruff format . before committing)
Linter: Ruff (run ruff check . — zero errors required)
Type checker: Mypy (run mypy core/ — zero errors in core)
Line length: 100 characters
Quotes: Double quotes (") for strings
Imports: Sorted by Ruff (stdlib → third-party → local)
Architecture Rules
No vendor imports in core/. Core must never import openai, anthropic, ollama, psycopg2, or any external service package.
Contracts are frozen dataclasses. All request/response types use @dataclass(frozen=True).
Capabilities implement the Capability ABC. No exceptions.
Registry pattern for discovery. Capabilities register with CapabilityRegistry, never hardcoded.
Logging via core.log. Use get_logger(__name__) in all modules.
What NOT to Do
Do not add runtime dependencies without team discussion.
Do not modify core/contracts/ without updating all dependent tests.
Do not commit .env, API keys, databases, or .venv/.
Do not "improve" existing code outside the current sprint scope without raising it first.
Pull Request Checklist
Before requesting review, verify:

 All tests pass (python -m unittest discover -s tests -v)
 Ruff lint is clean (ruff check .)
 Ruff format is clean (ruff format --check .)
 Mypy passes on core (mypy core/)
 No secrets or credentials in the diff
 Documentation updated if behavior changed
 Commit messages follow convention
 Sprint scope boundaries respected
Reporting Issues
If you discover a bug or architectural concern:

Check existing issues first.
Include reproduction steps.
Specify which sprint/component is affected.
Do not attempt to fix cross-boundary issues without discussion.
Questions?
Refer to:

Architecture Spec
Development Guide
Contract Reference
Roadmap