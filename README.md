# NAV — Navigate · Augment · Venture (v0)

NAV is a personal AI system designed around modular capabilities, a hybrid AI routing strategy, and a voice-first interface.

## Core Capabilities (v0)

```text
Cognition — Understand requests, reason, and produce responses.
Memory    — Retain and retrieve useful user context.
Research  — Discover, retrieve, and synthesize external information.
Sprint Status
Sprint    Theme    Status
S1    Project Structure & Architectural Skeleton    ✅ Complete
S2    Prerequisites & Environment Verification    ✅ Complete
S3    First Real AI Capability (Cognition)    ✅ Complete
S4    Voice Interface (Hear / Speak)    🔜 Next
Architecture Overview
NAV follows stable contracts over stable implementations. Core coordinates capabilities through abstract interfaces without vendor lock-in.

text

                     NAV v0
                       │
                  ┌────▼────┐
                  │ NAV Core │
                  └────┬────┘
                       │
             ┌─────────┼─────────┐
             │         │         │
         Cognition   Memory   Research
             │         │         │
             └─────────┼─────────┘
                       │
                AI Gateway
                       │
              ┌────────┴────────┐
              │                 │
         Ollama (local)    OpenAI (API)
         mistral default   gpt-4o-mini
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

# Run the test suite (no API key required)
python -m unittest discover -s tests -v

# Run linting and formatting checks
ruff check .
ruff format --check .

# Run type checking
mypy core/ ai/ capabilities/cognition/
Running NAV with AI
Default: Local Ollama (Free, No API Key)
Install Ollama and pull a model:
PowerShell

ollama pull mistral
Ensure Ollama is running (default: http://localhost:11434).
Run the live integration test:
PowerShell

python -m unittest tests.test_integration_live -v
Alternative: OpenAI (Paid API)
Copy the environment template and add your key:
PowerShell

Copy-Item .env.example .env
# Edit .env: set NAV_AI_PROVIDER=openai and NAV_OPENAI_API_KEY=sk-...
Load environment variables and run:
PowerShell

$env:NAV_AI_PROVIDER = "openai"
$env:NAV_OPENAI_API_KEY = "sk-your-key"
python -m unittest tests.test_integration_live -v
