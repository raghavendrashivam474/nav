# S13 Implementation Details

S13 introduces the **Memory Intelligence Layer** inside the `capabilities/memory/` module. The implementation is lightweight, relying entirely on Python’s standard library and SQLite.

---

## 1. Vocabulary & Metadata Injection (ADR-007)

Instead of altering the stable, frozen `MemoryRecord` contract structure, S13 injects semantic metadata directly into the existing `MemoryRecord.metadata: dict[str, Any]` field under well-known keys.

We introduced `capabilities/memory/semantics.py` containing four main Enums:
- `MemoryType`: `fact`, `preference`, `decision`, `goal`, `commitment`, `observation`, `instruction`, `temporary`
- `Importance`: `low`, `normal`, `high`, `critical`
- `Confidence`: `explicit`, `inferred`, `observed`, `imported`, `system`
- `LifecycleStatus`: `active`, `superseded`, `archived`

The helper `apply_defaults(metadata)` ensures that records stored without explicit metadata automatically get initialized to `fact`/`normal`/`explicit`/`active`.

---

## 2. SQLite Database Schema Migration

To support performance-optimized index queries, the `SQLiteMemoryRepository` extends its database schema to store metadata attributes in dedicated columns. 

On initialization, the repository executes a safe, idempotent migration using `PRAGMA table_info(memories)`:
```python
_S13_COLUMNS = [
    ("memory_type", "TEXT DEFAULT 'fact'"),
    ("importance", "TEXT DEFAULT 'normal'"),
    ("confidence", "TEXT DEFAULT 'explicit'"),
    ("lifecycle_status", "TEXT DEFAULT 'active'"),
    ("provenance", "TEXT DEFAULT ''"),
    ("valid_from", "TEXT"),
    ("valid_until", "TEXT"),
]
```

If any column is missing, the repository appends it dynamically using `ALTER TABLE`.

---

## 3. Intelligent Retrieval & Relevance Filtering

The SQLite `find()` query engine is upgraded to compile optional semantic filters:

- **Exact Matches:** Checks `memory_type`, `confidence`, and `lifecycle_status`.
- **Minimum Importance Filtering:** Calculates priority rank. If `min_importance="high"`, it constructs an `IN ('high', 'critical')` clause, filtering out `low` and `normal` records at the database level.

---

## 4. Lifecycle Transitions (Supersession)

The `supersede(old_key, new_record)` workflow implements Decision Evolution History without discarding past architectural choices:

- Marks the old record's `lifecycle_status` as `"superseded"` and populates `superseded_by` with the new record's key.
- Writes the new record with `supersedes` pointing back to the old key.

This creates a traceable bidirectional chain from the original decision to the current active choice.

---

## 5. Contradiction Detection

`detect_contradictions(record)` flags logical collisions. A potential contradiction is identified when:

- An existing active record has the same type as the candidate record.
- They share overlapping tags (e.g., `["ai", "preference"]`).
- Their values differ (e.g., prefer local AI vs. prefer cloud AI).

This logic flags anomalies immediately during the store loop without attempting auto-resolution, which remains a capability of higher cognition layers.

