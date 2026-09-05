# ADR-007: Memory Intelligence Semantics via Metadata Enrichment

## Status
Accepted

## Context
S13 requires intelligent memory semantics: classification, importance,
confidence/provenance, temporal validity, lifecycle management, and
relevance-aware retrieval. The existing MemoryRecord contract is a
frozen dataclass with key, value, tags, and metadata fields. The
metadata dict is currently underutilized (only timestamps).

## Decision
1. Define semantic enums (MemoryType, Importance, Confidence,
   LifecycleStatus) in `capabilities/memory/semantics.py`.
2. Store semantics in the existing `MemoryRecord.metadata` dict
   under well-known keys. No changes to MemoryRecord itself.
3. Extend `MemoryQuery` with optional filter fields (memory_type,
   min_importance, confidence, lifecycle_status) — all default to
   None, preserving backward compatibility.
4. Add `get(key)` to `MemoryRepository` ABC for lifecycle operations
   (supersede requires reading the old record before updating it).
5. Extend SQLite schema with dedicated columns for semantic fields
   to enable indexed filtering without JSON parsing in queries.
6. Auto-apply semantic defaults in `MemoryService.store()` so
   existing callers get sensible defaults without code changes.

## Consequences
- Backward compatible: all existing MemoryRecord/MemoryQuery
  construction sites continue to work unchanged.
- Existing memories get default semantics (fact/normal/explicit/active)
  via SQLite column defaults.
- No new infrastructure required — SQLite handles all S13 needs.
- The MemoryRepository ABC gains one method (get), which is a
  breaking change for external implementations but low-risk since
  only SQLiteMemoryRepository exists.
- S14 can consume semantic metadata to build the Memory→Context
  relevance pipeline without further Memory changes.
