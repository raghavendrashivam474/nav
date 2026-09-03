# NAV v0 Architecture — Sprint 1 Design Spec

NAV follows: **Stable contracts over stable implementations.**

## 1. Architectural Boundaries
* **Core (core/)**: System coordinator and contract baseline.
* **Capabilities (capabilities/)**: Modular capabilities: cognition, memory, and esearch.
* **AI Layer (i/)**: Gateway and model routing across local, ree, and paid providers.
* **Interfaces (interfaces/)**: Voice-first primary interface with text fallback.
* **Security (security/)**: Security, secrets, permissions, and policy boundaries.
* **Data (data/)**: Local and persistent storage boundary.

## 2. Status
* **Implemented in S1**: Core contracts, Registry, Orchestrator, Cognition stub, Unit tests.
* **Intentionally Not Locked**: AI model vendors, persistent databases, STT/TTS engines.
