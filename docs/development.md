# NAV Development Guide

## Prerequisites

- Python 3.10 or higher (verified on 3.13)
- Git
- PowerShell (Windows) or Bash (Linux/macOS)
- Ollama (optional, for local AI — recommended)

## Initial Setup

```powershell
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
│   ├── cognition/         # Understanding & reasoning (S3: AI-powered)
│   ├── memory/            # Retention & retrieval (stub)
│   └── research/          # Information discovery (stub)
├── ai/                    # AI provider layer (S3)
│   ├── errors.py          # NAV-level AI error hierarchy
│   ├── gateway/           # AIGateway implementation
│   └── providers/         # Ollama, OpenAI adapters
├── interfaces/            # User-facing layers (future)
├── security/              # Security enforcement boundary (future)
├── data/                  # Persistent storage (git-ignored, future)
├── tests/                 # Test suite
├── docs/                  # Documentation
├── pyproject.toml         # Single authoritative project config
├── .env.example           # Environment variable template
└── .gitignore
Development Commands
Testing
PowerShell

# Run all tests (no API key required — live tests auto-skip)
python -m unittest discover -s tests -v

# Run specific test module
python -m unittest tests.test_contracts -v
python -m unittest tests.test_cognition -v
python -m unittest tests.test_ai_provider -v
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

# Type-check core + AI + cognition
mypy core/ ai/ capabilities/cognition/

# Type-check full project
mypy .
AI Provider Configuration (S3)
NAV supports two AI providers out of the box. The active provider is selected via environment variable.

Default: Ollama (Local, Free)
Install Ollama and pull a model:
PowerShell

ollama pull mistral
Ensure Ollama is running (default: http://localhost:11434).
No environment variables needed — ollama is the default.
Run the live test:
PowerShell

python -m unittest tests.test_integration_live -v
Alternative: OpenAI (Paid API)
Copy the environment template:
PowerShell

Copy-Item .env.example .env
Edit .env:
text

NAV_AI_PROVIDER=openai
NAV_OPENAI_API_KEY=sk-your-key-here
NAV_OPENAI_MODEL=gpt-4o-mini
Load variables and run:
PowerShell

$env:NAV_AI_PROVIDER = "openai"
$env:NAV_OPENAI_API_KEY = "sk-..."
python -m unittest tests.test_integration_live -v
Environment Variables Reference
Variable    Default    Description
NAV_AI_PROVIDER    ollama    Active provider: ollama or openai
NAV_OLLAMA_URL    http://localhost:11434/api/chat    Ollama API endpoint
NAV_OLLAMA_MODEL    mistral    Ollama model name
NAV_OPENAI_API_KEY    (empty)    OpenAI API key (required if provider=openai)
NAV_OPENAI_MODEL    gpt-4o-mini    OpenAI model name
Note: The normal test suite (python -m unittest discover -s tests -v) does not require any API key or running Ollama instance. Live integration tests are skipped automatically when the provider is unavailable.

Development Conventions
Contracts First: Any new capability must implement the base Capability interface from core.contracts.capability.
Zero Vendor Leakage in Core: core/ must never import specific vendor packages.
Registry Pattern: Capabilities register with CapabilityRegistry and are invoked via Orchestrator.
Logging: Use core.log.get_logger(__name__) for all component logging.
Git Hygiene: Never commit keys, .env files, databases, .venv/, or __pycache__/.
Dependencies: All dependencies managed through pyproject.toml. Do not add requirements.txt.
Provider Isolation: Provider-specific SDKs and logic belong in ai/providers/, never in core/ or capabilities/.
Adding a New AI Provider
Create ai/providers/<name>_provider.py.
Implement a class with a complete(request: AIRequest) -> AIResponse method.
Translate provider errors into ai.errors.ConfigurationError or ai.errors.ProviderError.
Add the provider option to ai/gateway/default_gateway.py.
Add environment variables to .env.example.
Add unit tests with mocked HTTP in tests/test_ai_provider.py.
Adding a New Capability
Create capabilities/<capability_name>/.
Subclass core.contracts.capability.Capability.
Implement name, version, description, and invoke(request).
Use core.log.get_logger(__name__) for logging.
Add corresponding tests under tests/.
Register with CapabilityRegistry.
Dependency Management
All dependencies are declared in pyproject.toml:

dependencies — Runtime dependencies (httpx as of S3)
[project.optional-dependencies] dev — Development tooling (ruff, mypy)
To add a new runtime dependency:

toml

dependencies = [
    "httpx>=0.27.0",
    "some-package>=1.0.0",
]
Then reinstall:

PowerShell

pip install -e ".[dev]"
