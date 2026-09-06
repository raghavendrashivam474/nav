# S25 Sprint Plan: Evidence Synthesis, Conflict Resolution & Reasoned Findings

## Mission

Give NAV a deterministic foundation for synthesizing multiple evidence items into structured findings while explicitly preserving support, contradiction, uncertainty, and provenance.

## Architectural Approach

**Case A — Purely Additive.**
Zero existing files modified (except exports in `__init__.py`).
Consumes S24 Evidence contracts directly.

## Key Decisions

1. **Deterministic Synthesis:** Relies solely on explicit S24 `EvidenceRelation` edges. No LLMs, NLP, or semantic embeddings.
2. **Epistemic Honesty:** Conflict is represented (`CONTESTED`), not resolved arbitrarily. Support is marked `SUPPORTED`, not declared absolute truth.
3. **Four Finding States:** `SUPPORTED`, `CONTESTED`, `INCONCLUSIVE`, `INSUFFICIENT_EVIDENCE`.
4. **End-to-End Provenance:** `Finding` → `evidence_basis` → `Evidence` → `SourceMetadata` → S23 acquisition.
5. **No Ghost Evidence:** Non-successful S23 acquisitions cannot produce evidence or findings.
