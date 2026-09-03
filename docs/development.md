
NAV Development Guide
Prerequisites
Python 3.10 or higher (verified on 3.13)
Git
PowerShell (Windows) or Bash (Linux/macOS)
Initial Setup
PowerShell

# 1. Clone the repository
git clone <repo-url>
cd NAV

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate        # Linux/macOS

# 4. Install project with dev dependencies
pip install -e ".[dev]"

# 5. Verify installation
python -m unittest discover -s tests -v
Project Layout
text

NAV/
├── core/                  # System nucleus (contracts, registry, orchestration, logging)
│   ├── contracts/         # Typed interfaces (Capability, AI, Memory, Research, Context)
│   ├── context/           # Context models
│   ├── capabilities/      # Capability registry
│   ├── orchestration/     # Request routing
│   └── log.py             # Logging foundation
├── capabilities/          # Replaceable capability modules
│   ├── cognition/         # Understanding & reasoning
│   ├── memory/            # Retention & retrieval
│   └── research/          # Information discovery
├── ai/                    # Hybrid AI layer
│   ├── gateway/           # Uniform invocation
│   ├── router/            # Model routing policy
│   ├── policies/          # Routing constraints
│   └── providers/         # local/ free/ paid/
├── interfaces/            # User-facing layers
│   ├── voice/             # Voice-first (STT/TTS)
│   └── text/              # Text fallback
├── security/              # Security enforcement boundary
├── data/                  # Persistent storage (git-ignored)
├── tests/                 # Test suite
├── docs/                  # Documentation
├── scripts/               # Build/utility scripts
├── pyproject.toml         # Single authoritative project config
├── .env.example           # Environment variable template
└── .gitignore
Development Commands
Testing
PowerShell

# Run all tests
python -m unittest discover -s tests -v

# Run specific test module
python -m unittest tests.test_contracts -v
python -m unittest tests.test_logging -v
Linting & Formatting (Ruff)
PowerShell

# Check for lint issues
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Check formatting
ruff format --check .

# Auto-format
ruff format .
Type Checking (Mypy)
PowerShell

# Type-check core contracts
mypy core/

# Type-check full project
mypy .
Development Conventions
Contracts First: Any new capability must implement the base Capability interface from core.contracts.capability.
Zero Vendor Leakage in Core: core/ must never import specific vendor packages (e.g., openai, anthropic, psycopg2).
Registry Pattern: Capabilities register with CapabilityRegistry and are invoked via Orchestrator.
Logging: Use core.log.get_logger(__name__) for all component logging.
Git Hygiene: Never commit keys, .env files, databases, .venv/, or __pycache__/.
Dependencies: All dependencies managed through pyproject.toml. Do not add requirements.txt.
Environment Configuration
Copy .env.example to .env and fill in values as needed:

PowerShell

Copy-Item .env.example .env
The .env file is git-ignored. Never commit real credentials.

Adding a Capability
Create capabilities/<capability_name>/.
Subclass core.contracts.capability.Capability.
Implement name, version, description, and invoke(request).
Use core.log.get_logger(__name__) for logging.
Add corresponding tests under tests/.
Register with CapabilityRegistry.
Dependency Management
All dependencies are declared in pyproject.toml:

dependencies — Runtime dependencies (stdlib only at this stage)
[project.optional-dependencies] dev — Development tooling
To add a new runtime dependency:

toml

dependencies = [
    "some-package>=1.0.0",
]
Then reinstall:

PowerShell

pip install -e ".[dev]"