# NAV Development Guide

## Prerequisites

- Python 3.10 or higher (verified on 3.10-3.13)
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
│   ├── cognition/         # Understanding & reasoning (AI-powered)
│   ├── memory/            # Retention & retrieval (stub)
│   └── research/          # Information discovery (stub)
├── ai/                    # AI provider layer (S3 + S5)
│   ├── errors.py          # NAV-level AI error hierarchy with RoutingError
│   ├── gateway/           # AIGateway implementation with ModelRouter
│   ├── providers/         # Ollama, OpenAI adapters, AIProvider Protocol
│   └── routing/           # ModelRouter, RoutingContext, ProviderMetadata
├── interfaces/            # User-facing layers (S4: Voice)
├── security/              # Security enforcement boundary (future)
├── data/                  # Persistent storage (git-ignored, future)
├── tests/                 # Test suite
├── docs/                  # Documentation
├── pyproject.toml         # Authoritative project configuration
├── .env.example           # Environment variable template
└── .gitignore
Development Commands
Testing
PowerShell

# Run all unit tests (fast, mock-based, no external hardware/APIs required)
python -m unittest discover -s tests -v

# Run specific test modules
python -m unittest tests.test_routing -v
python -m unittest tests.test_cognition -v
python -m unittest tests.test_ai_provider -v
python -m unittest tests.test_voice_interface -v
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

# Type-check the whole project
mypy ai/ core/ capabilities/ interfaces/ tests/
AI Routing Configuration (S5)
NAV intelligently routes AI requests according to configured policies, constraints, and preferences.

How Routing Works
When an AI request is created, callers can supply routing hints in AIRequest.options["routing"]:

Python

from core.contracts.ai import AIMessage, AIRequest

request = AIRequest(
    messages=[AIMessage(role="user", content="Summarize private notes.")],
    options={
        "routing": {
            "privacy": "local_only",      # Constraint: must only use local provider
            "quality": "standard",        # Preference: standard vs high
            "cost": "low",                # Preference: low cost favored
        }
    }
)
The gateway's ModelRouter:

Applies Hard Constraints: Excludes remote providers when privacy="local_only".
Ranks Preferences: Evaluates matching attributes (cost, quality, latency).
Executes with Fallback: Tries the top candidate and automatically falls back to secondary options if a provider fails — while strictly never violating hard constraints.
Provider Environment Configuration
Configure your available providers in .env:

ini

# Preferred/Default Provider
NAV_AI_PROVIDER=ollama

# Local Ollama Configuration
NAV_OLLAMA_URL=http://localhost:11434/api/chat
NAV_OLLAMA_MODEL=mistral

# OpenAI Configuration (optional)
NAV_OPENAI_API_KEY=sk-...
NAV_OPENAI_MODEL=gpt-4o-mini
Adding a New AI Provider
Create ai/providers/<name>_provider.py.
Implement the AIProvider protocol (complete(request: AIRequest) -> AIResponse).
Map internal network/API errors to ai.errors.ProviderError or ai.errors.ConfigurationError.
Register the provider and its ProviderMetadata inside DefaultAIGateway._init_providers().
Add unit tests with mock responses in tests/test_ai_provider.py.
