# S16 Implementation Notes

## What was built
1. `ActivityType` enum + `InvestigationActivity` dataclass in `capabilities/research/investigation/models.py`
2. `activity_log` field on `Investigation` (default empty tuple, backward compatible)
3. Activity logging in all `InvestigationService` mutation methods
4. `capabilities/research/investigation/continuity/` subpackage:
   - `InvestigationContinuation` snapshot model
   - `ResolutionMatch` / `ResolutionResult` models
   - `InvestigationContinuityService` with resolve, build_continuation, resume
5. SQLite serialization extended for `activity_log` (backward compatible)
6. Comprehensive test suite in `tests/test_s16_investigation_continuity.py` (26 new tests)

## Architecture decisions
- Continuity is a separate subpackage, not merged into InvestigationService
- Resolution is deterministic scoring (no LLM, no vector search)
- Continuation snapshots are derived, never persisted separately
- Activity log lives in the JSON data blob (no schema migration needed)
- No Orchestrator changes — S16 provides the service layer only

## Backward compatibility
- All S15 tests pass unchanged
- Old investigations without activity_log deserialize to empty tuple
- No API changes to existing InvestigationService methods
- No changes to Research contracts, Memory, Context, or Orchestrator
