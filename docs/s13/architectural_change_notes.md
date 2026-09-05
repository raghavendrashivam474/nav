# S13 Architectural Change Notes

This document captures the intentional, backward-compatible updates made to NAV’s architecture during the S13 sprint.

---

## 1. Summary of Changes

Two minor contract adjustments were made to support S13 Memory Intelligence:
1. **`MemoryQuery` Extension (`core/contracts/memory.py`):** Added four optional query parameters:
   - `memory_type: str | None = None`
   - `min_importance: str | None = None`
   - `confidence: str | None = None`
   - `lifecycle_status: str | None = None`
2. **`MemoryRepository` ABC Update (`capabilities/memory/repository.py`):** Added the abstract lookup method `get(key) -> MemoryRecord | None`.

These changes were executed in full compliance with **ADR-007**.

---

## 2. Justification and Impact

### Why get(key) was necessary
The `supersede(old_key, new_record)` lifecycle operation requires:
1. Fetching the original record by its key.
2. Appending lifecycle metadata indicating it is superseded.
3. Updating the record.

Without `get(key)`, the repository only offered query-based lookup (`find(query)`), which is slow, non-deterministic for key-based edits, and introduces unnecessary overhead.

### Backward Compatibility Guarantee
- **Existing construction sites:** Since all new fields in `MemoryQuery` default to `None`, every existing query instantiation continues to compile and execute identically.
- **External repository implementations:** The addition of `get()` on the repository ABC technically breaks any custom external implementations. However, only `SQLiteMemoryRepository` exists inside NAV, making the migration risk extremely low.
- **SQLite Database Compatibility:** Existing databases are safely migrated on initialization using standard, idempotent SQL `ALTER TABLE ADD COLUMN` commands.
