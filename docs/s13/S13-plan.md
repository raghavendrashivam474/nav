# S13 Sprint Plan — Memory Intelligence

**Sprint:** S13 — Memory Intelligence  
**Target Release:** `v1.3`  
**Baseline:** `v1.2`  
**Status:** Executed  

---

## 1. Objectives

The central goal of S13 is to make NAV’s memory subsystem capable of semantic reasoning, structured lifecycle transitions, and conflict awareness without introducing complex dependencies (e.g., vector databases or graph databases).

Specifically, S13 must establish:
1. **Memory Classification:** Categorize memories (Facts, Preferences, Decisions, Goals, Commitments, etc.) to drive differentiated processing.
2. **Importance Scoring:** Differentiate trivial details from critical facts.
3. **Confidence & Provenance:** Explicitly track how a memory was acquired (explicit vs. inferred) and its origin.
4. **Temporal Boundaries:** Support temporal validity windows (`valid_from`, `valid_until`).
5. **Lifecycle Management:** Support active, superseded, and archived states.
6. **Contradiction Detection:** Flag when new memory entries conflict with existing active knowledge.
7. **Decision Memory:** Create a foundation for tracing the evolution of structural user decisions.

---

## 2. Scope & Boundaries

We strictly maintain the boundaries defined in S12:
- **Memory:** What NAV has deliberately retained permanently. (S13 target)
- **Context:** What is relevant to the user’s situation right now. (S12 foundation, untouched in S13)
- **Session:** The transient state of the active interaction loop. (Untouched)
- **Research:** Active, short-lived investigation maps. (Untouched)

### Non-Goals for S13
- No automatic promotion of Memories to active Context (deferred to S14).
- No vector database (e.g., Chroma, Qdrant) or Graph database (e.g., Neo4j).
- No LLM-powered background agents.
- No modifications to the Orchestrator or Cognition execution pipelines.

---

## 3. Implementation Plan (10-Step Execution)

- **Step 1 — Baseline:** Document pytest (296 tests), ruff, and mypy status.
- **Step 2 — Semantics Definition:** Create `semantics.py` containing clean Enums and default helpers.
- **Step 3 — Contract Extension:** Add optional filtering fields to `MemoryQuery` in `core/contracts/memory.py` without breaking compatibility.
- **Step 4 — Repository Interface Update:** Add `get(key)` to `MemoryRepository` ABC.
- **Step 5 — SQLite Extension:** Add S13 semantic columns to SQLite repository with idempotent migrations and filter logic inside `find()`.
- **Step 6 — Service Enrichment:** Implement auto-default metadata injection, `supersede()` lifecycle tracking, and tag-based `detect_contradictions()`.
- **Step 7 — Exports Update:** Export semantics via the capabilities module `__init__.py`.
- **Step 8 — S13 Test Coverage:** Write robust unit and scenario tests covering every new semantic vector (type, importance, confidence, etc.).
- **Step 9 — Regression Testing:** Verify that all 296 baseline S6-S12 tests remain green.
- **Step 10 — Release Documentation:** Complete sprint reports and close the sprint.
