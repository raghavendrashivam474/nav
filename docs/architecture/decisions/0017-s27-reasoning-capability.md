# ADR 0017: S27 Reasoning Capability Architecture

## Status
Accepted

## Context
As of NAV v2.3, the system could successfully retrieve external information (S23), evaluate and trace evidence (S24), deterministically synthesize findings (S25), and compare subjects along explicit dimensions (S26). However, the system lacked a structured representation for *why* a specific set of evidence/findings leads to a conclusion. 

Without an explicit reasoning primitive, the system is susceptible to opaque, non-inspectable model decisions, breaking NAV's core mandate of traceability and verifiable provenance.

## Decision
We establish a first-class **Reasoning capability** in S27 with the following architecture:

1. **Explicit Reasoning Contracts:** All reasoning activities must map to a formal, immutable schema containing discrete `ReasoningStep` items. Each step lists its explicit premises, inference style, description, and intermediate conclusions.
2. **Deterministic-First Architecture:** When reasoning over highly structured findings or comparative tables, the reasoning must occur deterministically to guarantee consistency and correctness.
3. **Model-Assisted Isolation:** For semantic reasoning over unstructured premises, the AI Gateway is utilized as an analytical tool, not an authority. Responses must match strict schemas and undergo validation and reference sanitization.
4. **Traceable Provenance:** A `ReasoningResult` must explicitly list its `finding_basis`, `evidence_basis`, and `comparison_basis` arrays to maintain complete provenance back to the S23 source documents.
5. **Separation of Reasoning and Decision:** Reasoning results state justifications, supporting factors, and conflicts. They do NOT make decisions (reserved for S28) or execute actions (reserved for S29).

## Consequences
- **Inspectability:** Users and downstream capabilities can inspect every logical step of a reasoning output.
- **Stability:** The reasoning engine is independent of the underlying LLM provider.
- **Safety:** Malformed model payloads, hallucinated references, and prompt injections are intercepted and safely mitigated.
- **Performance:** Deterministic reasoning bypasses the AI Gateway completely, optimizing latency and resource consumption.
