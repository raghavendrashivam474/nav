# NAV Architecture Overview

NAV (Navigate · Augment · Venture) is structured as a capability-oriented, offline-first AI system.

## Core Architectural Layers

```text
                         NAV
                          │
                     Orchestrator
                          │
             ┌────────────┼────────────┐
             ↓            ↓            ↓
         Cognition      Memory      Research
             │                         │
             │                  ResearchService
             │                         │
             │                 ┌───────┴────────┐
             │                 ↓                ↓
             │            Discovery        Retrieval
             │                                  │
             │                          bounded concurrency
             │                                  │
             │                                  ↓
             │                              Evidence
             │                                  │
             │                              Synthesis
             │                                  │
             └────────────┬─────────────────────┘
                          ↓
                     AI Gateway
                          ↓
                    Model Router
                          ↓
                      Providers
1. Orchestration Layer (core/orchestration/)
The Orchestrator receives standardized Request payloads and routes them to registered capabilities via CapabilityRegistry. Core remains completely decoupled from capability-internal implementations.

2. Capabilities Layer (capabilities/)
Cognition: Lightweight text-to-text reasoning and conversational responses.
Memory: Persistent structured recall using SQLite repository and key-value semantics.
Research: Deep, multi-step investigation combining source candidate discovery, bounded parallel retrieval, evidence extraction, and contradiction/uncertainty synthesis.
3. S8 Research Subsystem
Bounded Concurrency (concurrency.py): Independent source fetching runs via a managed ThreadPoolExecutor bounded by max_concurrent_retrievals (default: 4). Partial failures in one source do not block or cancel other sources.
Progress Reporting (progress.py): Decoupled ProgressEvent protocol emitting lifecycle milestones (STARTED, DISCOVERY, RETRIEVAL, EXTRACTION, SYNTHESIS, COMPLETED) to attached reporters without knowledge of caller modality (Voice, CLI, UI).
Prompt-Injection Hardening (security.py): Retrieved external data is treated as untrusted and wrapped in explicit <untrusted_source_data> tags with security instructions.
4. AI Gateway & Model Router (ai/)
Abstracts AI model providers (Ollama, OpenAI) behind a policy-driven ModelRouter. Providers are scored based on locality, privacy, cost, latency, and capability constraints.

5. Interfaces Layer (interfaces/)
Modality adapters (such as VoiceInterface and CLI) convert audio/text input into standard Request objects, execute through the orchestrator, and synthesize replies.
