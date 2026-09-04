# S12 Architectural Change Note: Personal Context Foundation

## Observed Problem
1. **No concrete ContextManager implementation**: S11 established the ContextManager abstract contract in core/context/context_manager.py, but no concrete implementation existed. The contract defined get_context(), update_user_context(), update_session_context(), and update_conversation_context() — all abstract.
2. **No personal context representation**: NAV had no mechanism for answering "What is relevant about the user's current situation right now?" Memory answered "What has been retained?" and Session answered "What interaction are we continuing?" but nothing bridged the gap to situational awareness.
3. **NavContext lacked personal context**: The NavContext snapshot contained user, session, conversation, mbient_data, and esearch — but no typed personal context field. The mbient_data dict could serve as a catch-all, but unstructured dicts do not scale into a reliable context system.

## Evidence
- core/context/context_manager.py contained only an ABC with four abstract methods.
- core/context/__init__.py exported only ContextManager.
- NavContext in core/contracts/context.py had no personal_context field.
- S11 ADR-003 explicitly stated: "Lays the clean architectural contract for personal context in S12+ without breaking existing S10 research continuity."
- The S12 brief (§6) specified five personal context domains: user context, active projects, goals, commitments, and current focus.

## Existing Components Responsible
- core/contracts/context.py: Defines NavContext, UserContext, SessionContext, ConversationContext, ResearchSessionContext.
- core/context/context_manager.py: Defines ContextManager ABC.
- capabilities/memory/: Owns durable memory storage (SQLite).
- capabilities/research/context_store.py: Owns research-specific volatile state.

## Architectural Changes Made in S12

### 1. Personal Context Dataclasses (core/contracts/context.py)
Added five frozen dataclasses representing explicit, user-declared personal context:
- Project: project_id, 
ame, status, description, priority, current_focus
- Goal: goal_id, description, status, priority, project_id
- Commitment: commitment_id, description, status
- CurrentFocus: project_id, goal_id, ctivity, 	opic
- PersonalContext: Aggregated snapshot of projects, goals, commitments, and focus.

All models are frozen (immutable) to match the existing NavContext snapshot pattern.

### 2. NavContext Extension (core/contracts/context.py)
Added personal_context: PersonalContext | None = None to NavContext. This is backward-compatible: all existing code that constructs NavContext without personal_context continues to work unchanged.

### 3. ContextStore (core/context/store.py)
New in-memory dict-based store providing isolated user, session, conversation, and personal context management. No external dependencies. Persistence beyond process lifetime is deferred to S13/S14.

### 4. DefaultContextManager (core/context/default_manager.py)
Concrete implementation of the S11 ContextManager ABC. Implements all four abstract methods and adds concrete personal-context methods (dd_project, dd_goal, dd_commitment, set_focus, etc.) beyond the ABC. The S11 ABC itself is unchanged.

### 5. Core Contracts Re-exports (core/contracts/__init__.py)
Added S12 types (Project, Goal, Commitment, CurrentFocus, PersonalContext) to the existing re-export list. All existing re-exports preserved.

### 6. Context Package Exports (core/context/__init__.py)
Updated to export ContextManager, DefaultContextManager, and ContextStore.

## Alternatives Considered & Rejected
- **Alternative A: Use mbient_data dict for personal context.**
  - *Rejected*: Unstructured dicts do not provide type safety, discoverability, or testability. The brief explicitly calls for typed context models.
- **Alternative B: Extend the ContextManager ABC with personal-context abstract methods.**
  - *Rejected*: The S11 ABC is a stable contract. Adding abstract methods would break any existing or future implementations. Concrete methods on DefaultContextManager provide the same functionality without contract instability. A future ADR may promote these to the ABC if evidence warrants it.
- **Alternative C: Use SQLite or external storage for personal context.**
  - *Rejected (S12 scope)*: The brief mandates "simplest storage that satisfies the requirements." In-memory is sufficient for S12. Persistence is deferred to S13/S14 when the Memory → Context relevance pipeline is built.
- **Alternative D: Integrate Context into the Orchestrator.**
  - *Rejected*: The brief (§17) explicitly warns against turning the Orchestrator into a context-management god object. Integration is deferred until evidence from S13/S14 justifies it.

## Backward Compatibility
100% preserved. All 246 existing v1.1 tests pass without modification. The personal_context field defaults to None, so all existing NavContext construction sites are unaffected.

## Verification
- 296 tests passing (246 baseline + 50 new S12 tests).
- Clean Ruff lint and format.
- Clean Mypy across all source files.
