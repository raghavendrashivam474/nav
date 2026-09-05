# NAV Architecture Reference (v0.9)

NAV (*Navigate · Augment · Venture*) is a modular, local-first personal intelligence system built around strict architectural boundaries, stable contracts, and replaceable implementations.

---

## Core System Topology

```text
                        User / Client
                              │
               ┌──────────────┴──────────────┐
               │                             │
        Voice Interface                CLI / API
         (STT / TTS)                         │
               │                             │
               └──────────────┬──────────────┘
                              │
                      NAV Orchestrator
                              │
               ┌──────────────┴──────────────┐
               │                             │
       Cognition Capability          Research Capability
               │                             │
          AI Gateway                    Live Search
               │                      (DuckDuckGo / Mock)
          Model Router                       │
               │                     Concurrent Retrieval
         Local / Remote AI           (HTML / Text / PDF)
        (Ollama / OpenAI)                    │
                                     Evidence Extraction
                                             │
                                     Evidence Synthesis
                                             │
                                     Progress Reporting
                                             │
                                       Security Layer
                                             │
                                       Memory Service
                                      (SQLite Storage)
                
Key Invariants (S1–S9)
- **Contract Stability:** Core contracts in `core/contracts/` are implementation-agnostic.
- **AI Decoupling:** AI providers are hidden behind `AIGateway` and selected via `ModelRouter`.
- **Interface Agnosticism:** Capabilities report progress via `ProgressReporter` without knowing the consumer.
- **Voice as Boundary:** Voice is a communication modality, not a reasoning layer.
- **Memory Discipline:** Memory is explicit; raw research sessions do not pollute memory automatically.
- **Security Hardening:** External web content is wrapped in `<untrusted_source_data>` tags and treated strictly as data.
- **Bounded Concurrency:** Source retrieval uses a bounded `ThreadPoolExecutor`.
- **Partial Failure Isolation:** Failure of an individual source does not fail the research query.
- **Pluggable Search & Documents:** Search engines implement `SearchProvider`; document parsers (PDF) implement `SourceRetriever`.

## Research Workflow Pipeline
```text

ResearchQuery
    │
    ▼
1. Discovery (DuckDuckGoSearchProvider / MockSearchProvider)
    │  Discovers SourceCandidates
    ▼
2. Provenance Tracking (ProvenanceTracker)
    │  Normalizes URLs, assigns stable source_ids
    ▼
3. Bounded Retrieval (retrieve_concurrently / HttpxRetriever)
    │  Fetches HTML, Text, or PDF via pypdf
    ▼
4. Evidence Extraction (EvidenceExtractor)
    │  Extracts structured claims using AI Gateway
    ▼
5. Evidence Synthesis (EvidenceSynthesizer)
    │  Synthesizes supported findings, conflicts, and uncertainties
    ▼
ResearchResult (with full provenance traceability)
```