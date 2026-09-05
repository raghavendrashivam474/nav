# S16 Architectural Change Notes

## Changes
1. **Additive field**: `activity_log: tuple[InvestigationActivity, ...] = ()` on `Investigation`
   - Backward compatible: default empty tuple, old records deserialize gracefully
2. **New subpackage**: `capabilities/research/investigation/continuity/`
   - Purely additive, no existing code modified
3. **Activity logging**: `InvestigationService` mutation methods now record activities
   - Does not change return types or method signatures
   - Only adds entries to the activity_log tuple

## No breaking changes
- `InvestigationRepository` interface unchanged
- `InvestigationService` public API unchanged
- SQLite schema unchanged (`activity_log` in JSON blob)
- All S1–S15 tests pass
