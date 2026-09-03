# S7 Sprint Completion Report: Research Capability

**Sprint:** S7  
**Milestone:** `v0.7`  
**Status:** Complete  
**Date:** September 2026  

---

## 1. Executive Summary

Sprint S7 introduces NAV's first **Research Capability**. Rather than behaving as an opaque LLM wrapper or conversational memory store, NAV systematically investigates complex questions, discovers sources, enforces provenance, organizes evidence, surfaces uncertainties and contradictions, and maps out open questions without prematurely deciding for the user.

---

## 2. Mandatory Questions (§46)

### What did we build?
We built a systematic research subsystem in `capabilities/research/` following the strict separation of **Deterministic Infrastructure** and **AI-Assisted Analysis**:
1. **Source Discovery (`discovery.py`):** Pluggable `SearchProvider` protocol with bounded candidate discovery and offline mock support.
2. **Retrieval (`retrieval.py`):** `HttpxRetriever` and `MockRetriever` enforcing streaming content budgets, connection limits, and timeout isolation.
3. **URL Normalization & Provenance (`provenance.py`):** Canonical URL deduplication, stable source IDs (`src_*`), and strict evidence-to-source traceability matrix (`ev_* -> src_*`).
4. **AI-Assisted Extraction (`extraction.py`):** Structured claim extraction using S5 routing (`task_type="research_extraction"`), with fallback heuristic parsing.
5. **AI-Assisted Synthesis (`synthesis.py`):** High-level mapping into categorical findings, contradictions, uncertainties, and open questions using S5 high-quality routing (`task_type="research_synthesis"`).
6. **Research Workflow Engine (`service.py`):** Orchestrates discovery, deduplication, retrieval, extraction, and synthesis.
7. **Research Capability (`capability.py`):** Registered with the Orchestrator as `"research"` and implements `ResearchCapabilityInterface`. Supports optional persistence of durable findings to memory.

### What files changed / were added?
- **Contracts:**
  - `core/contracts/research.py` (Evolved)
- **Research Capability:**
  - `capabilities/research/__init__.py`
  - `capabilities/research/capability.py`
  - `capabilities/research/service.py`
  - `capabilities/research/discovery.py`
  - `capabilities/research/retrieval.py`
  - `capabilities/research/extraction.py`
  - `capabilities/research/synthesis.py`
  - `capabilities/research/provenance.py`
- **Tests:**
  - `tests/test_research.py` (New comprehensive test suite)
  - `tests/test_contracts.py` (Type refinement)
  - `tests/test_cognition.py` (Type refinement)
- **Demos & Docs:**
  - `demo_s7.py`
  - `docs/s7/completion-report.md`
  - `docs/architecture.md`
  - `docs/development.md`
  - `.env.example`

### What existing architecture remained untouched?
- `core/contracts/capability.py` — Untouched
- `core/contracts/memory.py` — Untouched
- `core/contracts/ai.py` — Untouched
- `core/orchestration/orchestrator.py` — Untouched
- `core/capabilities/registry.py` — Untouched
- `capabilities/cognition/` — Untouched
- `capabilities/memory/` — Untouched
- `interfaces/voice/` — Untouched
- `ai/gateway/` — Untouched
- `ai/routing/` — Untouched
- `ai/providers/` — Untouched

### Did any contracts change? Why?
Yes. `core/contracts/research.py` was evolved per §25 and §44 of the implementation brief. The initial v0.1 sketch only contained `ResearchQuery(terms, depth, whitelist)` and `ResearchResult(query, sources: list[dict], synthesis: str)`. It lacked data representations for:
- Structured `ResearchSource` metadata and retrieval lifecycle (`SourceStatus`).
- Structured `ResearchEvidence` linked to source IDs.
- Categorical uncertainty representation (`SupportState`).
- Multi-dimensional research maps (findings, conflicts, uncertainties, open questions).
- `SearchProvider` and `SourceRetriever` protocols.

### Did Core change?
No. `core/` contracts outside `research.py` remained 100% identical.

### Did Cognition change?
No. Cognition remains focused on conversational reasoning and memory interaction. Research is a peer capability.

### Did Voice change?
No. Voice remains decoupled and transports audio to text requests routed through the Orchestrator.

### Did AI Gateway or S5 Routing change?
No. Research consumed `AIGateway` directly, supplying routing hints via `AIRequest.options["routing"]` (`task_type`, `complexity`, `quality`, `privacy`).

### Did S6 Memory change?
No. Memory's interface was consumed as an optional dependency to store selected high-confidence findings when `save_to_memory=True`.

---

## 3. Test & Verification Metrics

- **Unit & Integration Tests:** 133 passed, 1 skipped (live audio hardware test)
- **Regression:** Zero regressions across S1–S6 test suites
- **Linter (Ruff):** Clean (0 errors across codebase)
- **Type Checker (Mypy):** Clean (0 errors in 76 source files)
- **Network Independence:** 100% offline test suite using fakes and mocks
- **Live Demo (`demo_s7.py`):** Verified end-to-end execution

---

## 4. Architectural Findings & S8 Horizon

### Key Lessons from S7:
1. **Deterministic vs. AI Separation Works:** Retaining control over HTTP retrieval, size limits, and deduplication prevents model hallucinations and memory blowouts while preserving exact source provenance.
2. **Categorical Uncertainty is Robust:** Using categorical states (`SUPPORTED`, `CONFLICTING`, `INSUFFICIENT`, `UNKNOWN`) produces clear evidence maps without arbitrary numerical confidence scores.
3. **Workflow Composition:** A Capability can cleanly orchestrate multi-step workflows without altering NAV Core or Orchestrator boundaries.

### Opportunities for S8:
- Asynchronous / parallel retrieval and extraction for faster multi-source workflows.
- Streaming progress events during long research operations.
- PDF and local document parsers implementing `SourceRetriever`.
