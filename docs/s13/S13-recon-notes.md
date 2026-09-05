# S13 Reconnaissance Notes

**Date:** 2026-09-05
**Branch:** sprint/s13-memory-intelligence
**Baseline:** v1.2 (commit 0ecd4e1)

## 1. Existing Memory Architecture

### Location
`capabilities/memory/` — service.py, sqlite_repo.py, repository.py, capability.py

### Public Interfaces
- `MemoryCapabilityInterface` (ABC): store, retrieve, update, forget
- `MemoryRepository` (ABC): initialize, save, find, replace, delete
- `MemoryService`: implements MemoryCapabilityInterface + regex helpers

### Storage
SQLite via `SQLiteMemoryRepository`. Single `memories` table.
Schema: key(PK), value(JSON), tags(JSON), metadata(JSON), created_at, updated_at.

### Retrieval
Simple LIKE keyword matching on value and tags columns. ORDER BY updated_at DESC.

### Update
`replace()` preserves created_at, updates updated_at. Full row overwrite.

### Deletion
`delete()` by key. Hard delete, no soft-delete or history.

### Existing Metadata
Only `created_at` and `updated_at` are populated in the metadata dict.

### Existing Tests
`tests/test_memory.py` — 29 tests covering store, retrieve, update, forget, duplicates.

## 2. Existing Limitations

| Area | Limitation | Evidence |
|------|-----------|----------|
| Classification | None. All memories are untyped key-value pairs. | MemoryRecord has no type field |
| Importance | None. All memories treated equally. | No importance in schema or metadata |
| Confidence | None. No distinction between explicit and inferred. | No confidence/provenance fields |
| Provenance | None. No source tracking. | metadata only has timestamps |
| Temporal | Basic created_at/updated_at only. No validity windows. | Schema has no valid_from/until |
| Retrieval | Keyword LIKE only. No relevance scoring. | find() uses LIKE on value/tags |
| Contradiction | None. No detection or representation. | No comparison logic exists |
| Lifecycle | Active-only. No supersede/archive. Hard delete only. | delete() is permanent |

## 3. Architecture Impact Assessment

**S13 CAN be implemented within existing boundaries** with two small extensions:

1. Add optional filter fields to `MemoryQuery` (backward-compatible, defaults to None)
2. Add `get(key)` to `MemoryRepository` ABC (needed for supersede lifecycle)

Both are additive. No existing signatures change. No existing behavior changes.
All 296 existing tests will continue to pass.

## 4. Key Observations

- `metadata: dict[str, Any]` is the natural injection point for S13 semantics
- SQLite ALTER TABLE ADD COLUMN makes schema migration trivial and idempotent
- `MemoryRecord.value` is `Any` stored as JSON — can hold structured decision data
- The S12 PersonalContext models (Goal, Commitment) suggest memory types that bridge to context
- No infrastructure changes needed — SQLite handles everything S13 requires
