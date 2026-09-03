# NAV Architectural Blueprint

**Milestone:** `v0.7` (Sprint S7)

---

## 1. System Overview

NAV (**Navigate · Augment · Venture**) is designed around strict capability isolation, pluggable AI providers, policy-driven model routing, persistent memory, and systematic research.
text

                  User / Voice Interface
                            │
                            ▼
                        NAV Core
                            │
                            ▼
                       Orchestrator
                            │
     ┌──────────────────────┼──────────────────────┐
     ▼                      ▼                      ▼
Cognition Capability Memory Capability Research Capability
(Conversational AI) (SQLite Storage) (Systematic Workflow)
│ │ │
└──────────────────────┼──────────────────────┘
▼
AI Gateway
│
▼
Model Router
│
┌────────────┴────────────┐
▼ ▼
Ollama Provider OpenAI Provider

text


---

## 2. Research Capability Subsystem (S7)

Research operates under the rule: **Research owns research; AI does not own research.**
Research Query
│
▼
Research Service
│
├── 1. Discovery ──────► SearchProvider (Bounded candidates)
│
├── 2. Provenance ─────► ProvenanceTracker (URL normalization & dedup)
│
├── 3. Retrieval ──────► SourceRetriever (Size budget & timeout isolation)
│
├── 4. Extraction ─────► EvidenceExtractor (AI Gateway: research_extraction)
│
└── 5. Synthesis ──────► EvidenceSynthesizer (AI Gateway: research_synthesis)
│
▼
ResearchResult
(Findings + Conflicts + Uncertainties)

text


### Deterministic vs. AI Separation:
- **Deterministic Layer:** URL normalization, source deduplication, HTTP retrieval, timeout handling, content size truncation, provenance ID assignment (`src_*`, `ev_*`).
- **AI Layer:** Extracting relevant claims, categorizing support, identifying contradictions, framing open questions.

---

## 3. Capability Inventory

| Capability | Version | Description | Target |
|---|---|---|---|
| `cognition` | `0.2.0` | Conversational reasoning & memory interaction | Orchestrator / Gateway |
| `memory` | `0.1.0` | Durable persistent key-value & tagged storage | SQLite Repository |
| `research` | `0.1.0` | Systematic topic exploration and research mapping | Research Service |

---

## 4. Architectural Rules & Invariants
1. Core remains independent of specific capabilities.
2. Capabilities never invoke external AI providers directly; all AI interactions route through `AIGateway`.
3. Memory is optional; research results do not automatically pollute persistent memory unless explicitly requested.
4. External retrieved web content is treated as untrusted data and never dictates system policy.
