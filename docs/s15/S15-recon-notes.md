# S15 Recon Notes

## Recon Answers

### Existing Research

1. **What does Research currently do?**
   Single-shot query -> findings + sources. Delegates to ResearchProvider.

2. **What is its public contract?**
   `ResearchProvider.search(query) -> ResearchResult`

3. **What does it return?**
   ResearchResult containing: query, findings (list[ResearchFinding]),
   sources (list[ResearchSource]), summary, completed_at, error.

4. **Is research state currently persistent?**
   No. Results exist only in memory during the interaction.

5. **What information is currently lost after a research interaction?**
   Everything — findings, sources, the query itself, context around why
   the research was initiated.

6. **How are sources represented?**
   ResearchSource dataclass: title, url, snippet, relevance, retrieved_at.

7. **How are research failures handled?**
   ResearchResult.error field + .success property. Graceful degradation.

### Context

8. **How can Research access relevant current context?**
   Via ContextProvider.get_snapshot() -> ContextSnapshot.
   Orchestrator already gathers context before routing.

9. **Does existing ContextualSnapshot provide enough information?**
   Yes for initial S15. Contains active_project, recent_topics,
   current_goal, relevant_memories.

10. **Does Research actually need additional context integration?**
    Not for S15. The existing snapshot is sufficient to inform
    investigation creation.

### Memory

11. **How can existing Memory be consulted?**
    Via MemoryProvider.recall(query) -> list[MemoryEntry].

12. **Should Research write to Memory in S15?**
    Not automatically. Investigation state should live in its own
    persistence layer. Memory is for things NAV should remember
    long-term, not for investigation working state.

13. **If not, where should investigation state live?**
    Own persistence layer following SQLiteMemoryRepository pattern.
    SQLite database, abstract repository, concrete implementation.

### Architecture

14. **Where should an Investigation object live?**
    `capabilities/research/investigation/` — a sub-module within
    the existing research capability.

15. **Which existing boundary should own investigation lifecycle?**
    ResearchService should be extended (or a new InvestigationService
    created alongside it) to manage investigation lifecycle.

16. **Can this be implemented additively?**
    Yes. No existing contracts need to change. New models, new service,
    new repository, new tests — all additive.

17. **What existing contract would have to change, if any?**
    None. The existing ResearchProvider contract remains unchanged.
    InvestigationService will use ResearchService internally.

## Architecture Decision

S15 can be implemented **entirely additively**:
- New investigation models alongside existing research models
- New investigation repository following existing MemoryRepository pattern
- New investigation service that uses existing ResearchService
- No changes to existing contracts, context, memory, or orchestration
- Existing tests remain untouched

This is the ideal outcome for S15.
