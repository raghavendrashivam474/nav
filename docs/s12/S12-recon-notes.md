# S12 — Reconnaissance Notes

## Baseline Verification
- Branch: main at tag v1.1
- Commit: f8b8662 (docs(s11): add S11 plan, recon notes, baseline, change notes, and post-completion reports)
- Working tree clean
- Sprint branch created: sprint/s12-context-foundation

## Existing Context Package (core/context/)
- context_manager.py: ContextManager ABC with 4 abstract methods
  - get_context(session_id, user_id, conversation_id) -> NavContext
  - update_user_context(user_id, **preferences) -> UserContext
  - update_session_context(session_id, **metadata) -> SessionContext
  - update_conversation_context(conversation_id, turns_increment, history_summary) -> ConversationContext
- __init__.py: Exports ContextManager only

## Existing Context Contracts (core/contracts/context.py)
- UserContext (frozen): user_id, preferences dict
- SessionContext (frozen): session_id, metadata dict
- ConversationContext (frozen): conversation_id, turns_count, history_summary
- ResearchSessionContext (frozen): session_id, root_query, current_subtopic, depth_level, etc.
- NavContext (frozen): user, session, conversation, ambient_data dict, research (optional)

## Key Observation: ambient_data
NavContext already has an ambient_data: dict[str, Any] field that could
serve as a catch-all. However, the S12 brief explicitly calls for typed
personal context models to avoid unstructured sprawl. Decision: add a
typed personal_context field alongside ambient_data.

## Contracts __init__.py Re-exports
The existing __init__.py re-exports from:
- core.contracts.ai: AIGateway, AIMessage, AIRequest, AIResponse
- core.contracts.capability: Capability, Request, Response
- core.contracts.context: ConversationContext, NavContext, ResearchSessionContext, SessionContext, UserContext
- core.contracts.memory: MemoryCapabilityInterface, MemoryQuery, MemoryRecord
- core.contracts.research: 15 types (ContinuationIntent through SupportState)

IMPORTANT: Initial S12 implementation accidentally overwrote this with a
simplified version that dropped AI/Memory/Research imports, causing 29
collection errors across the entire test suite. Fixed by restoring the
full import structure and adding S12 types incrementally.

## Orchestrator (core/orchestration/orchestrator.py)
- Minimal: takes CapabilityRegistry, routes Request to Capability
- No context threading currently
- Decision: Do NOT modify orchestrator in S12 (deferred until evidence requires it)

## Request/Response
- No separate request.py/response.py files exist
- Request and Response live in core.contracts.capability

## Memory Subsystem (capabilities/memory/)
- capability.py, repository.py, service.py, sqlite_repo.py
- Owns SQLite persistence for MemoryRecord
- Decision: Do NOT touch

## Research Subsystem (capabilities/research/)
- context_store.py: ResearchContextStore (owns research session state)
- continuity.py: ContinuityResolver
- 15+ files for retrieval, extraction, synthesis, security, etc.
- Decision: Do NOT touch

## ADR-003 (Context Architecture)
- Established ContextManager ABC in S11
- NavContext remains top-level immutable snapshot
- Capability-specific volatile stores retain domain ownership
- "Lays the clean architectural contract for personal context in S12+"

## Test Baseline
- 246 passed, 1 skipped, 2 deselected (pre-S12)
- 31 test files in tests/
- No tests/context/ directory existed before S12
