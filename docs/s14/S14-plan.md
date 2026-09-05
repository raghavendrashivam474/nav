# S14 Implementation Plan — Memory → Context Integration

## Inputs
1. Current NavContext (from ContextManager.get_context())
2. Interaction hint (optional text describing current request)
3. MemoryCapabilityInterface (injected dependency)

## Processing
1. Extract relevance terms from PersonalContext dimensions:
   - Project names and focus areas
   - Goal descriptions
   - Commitment descriptions
   - Current focus topic and activity
   - Interaction hint text
2. Query Memory for active records matching relevance terms
3. Filter out superseded/archived memories (S13 lifecycle)
4. Rank by S13 semantics: importance, confidence, type relevance, tag overlap
5. Convert top results to MemoryContextItems preserving full provenance
6. Wrap in ContextualSnapshot with base NavContext unchanged

## Output
- ContextualSnapshot (frozen dataclass):
  - base_context: NavContext (unchanged reference)
  - relevant_memories: tuple of MemoryContextItem
  - interaction_hint: str
  - timestamp: str (ISO format)

## What S14 will NOT change
- NavContext dataclass
- PersonalContext dataclass
- ContextManager ABC
- DefaultContextManager
- ContextStore
- MemoryRecord / MemoryQuery contracts
- MemoryService
- MemoryRepository / SQLiteMemoryRepository
- Any S13 semantics
- Any existing tests

## New files
- core/context/integration.py (MemoryContextIntegrator, ContextualSnapshot, MemoryContextItem)
- tests/test_s14_memory_context_integration.py

## Modified files
- core/context/__init__.py (additive exports only)

## Architectural change needed?
- **No.** The existing MemoryCapabilityInterface ABC in core/contracts/memory.py
  provides the exact integration boundary needed. S14 depends only on core contracts.
