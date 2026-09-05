# S16 Plan — Investigation Continuity

## Goal
Enable NAV to meaningfully resume a persistent investigation across sessions.

## Approach
1. Add `InvestigationActivity` model + `activity_log` field to Investigation (additive).
2. Create `investigation/continuity/` subpackage with:
   - `InvestigationContinuation` snapshot model
   - `ResolutionResult` / `ResolutionMatch` models
   - `InvestigationContinuityService` (resolve + build_continuation + resume)
3. Add activity logging to InvestigationService mutation methods.
4. Extend SQLite serialization for activity_log (backward compatible).
5. Comprehensive tests.

## Non-goals
- No LLM summarization
- No Orchestrator rewrite
- No vector search
- No frontend
- No autonomous agent loop
