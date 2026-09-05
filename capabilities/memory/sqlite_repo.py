"""SQLite-backed MemoryRepository.

Uses only the Python standard-library `sqlite3` module.
No ORM, no external dependencies.

S13: Schema extended with semantic columns (memory_type, importance,
confidence, lifecycle_status, provenance, valid_from, valid_until).
Migration is idempotent via PRAGMA table_info inspection.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from capabilities.memory.repository import MemoryRepository
from capabilities.memory.semantics import IMPORTANCE_RANK
from core.contracts.memory import MemoryQuery, MemoryRecord
from core.log import get_logger

logger = get_logger(__name__)

# S13 columns to add idempotently
_S13_COLUMNS: list[tuple[str, str]] = [
    ("memory_type", "TEXT DEFAULT 'fact'"),
    ("importance", "TEXT DEFAULT 'normal'"),
    ("confidence", "TEXT DEFAULT 'explicit'"),
    ("lifecycle_status", "TEXT DEFAULT 'active'"),
    ("provenance", "TEXT DEFAULT ''"),
    ("valid_from", "TEXT"),
    ("valid_until", "TEXT"),
]


class SQLiteMemoryRepository(MemoryRepository):
    """Concrete repository that persists memories in a local SQLite file."""

    def __init__(self, db_path: str | Path = "data/nav_memory.db") -> None:
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Create the database file and schema if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                tags       TEXT NOT NULL DEFAULT '[]',
                metadata   TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # S13: idempotent schema migration
        existing_cols = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(memories)").fetchall()
        }
        for col_name, col_def in _S13_COLUMNS:
            if col_name not in existing_cols:
                self._conn.execute(f"ALTER TABLE memories ADD COLUMN {col_name} {col_def}")
                logger.info("S13 migration: added column %s", col_name)
        self._conn.commit()
        logger.info("SQLite memory DB ready at %s", self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.initialize()
        assert self._conn is not None
        return self._conn

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def save(self, record: MemoryRecord) -> bool:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        meta = dict(record.metadata)
        meta.setdefault("created_at", now)
        meta["updated_at"] = now

        # S13: extract semantic fields for dedicated columns
        mem_type = meta.get("memory_type", "fact")
        importance = meta.get("importance", "normal")
        confidence = meta.get("confidence", "explicit")
        lifecycle = meta.get("lifecycle_status", "active")
        provenance = meta.get("provenance", "")
        valid_from = meta.get("valid_from")
        valid_until = meta.get("valid_until")

        try:
            conn.execute(
                "INSERT INTO memories "
                "(key, value, tags, metadata, created_at, updated_at, "
                "memory_type, importance, confidence, lifecycle_status, "
                "provenance, valid_from, valid_until) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.key,
                    json.dumps(record.value),
                    json.dumps(record.tags),
                    json.dumps(meta),
                    meta["created_at"],
                    now,
                    mem_type,
                    importance,
                    confidence,
                    lifecycle,
                    provenance,
                    valid_from,
                    valid_until,
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug("Duplicate memory key: %s", record.key)
            return False

    def get(self, key: str) -> MemoryRecord | None:
        """S13: single-record lookup by primary key."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT key, value, tags, metadata FROM memories WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return MemoryRecord(
            key=row["key"],
            value=json.loads(row["value"]),
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
        )

    def find(self, query: MemoryQuery) -> list[MemoryRecord]:
        conn = self._get_conn()
        conditions: list[str] = []
        params: list[object] = []

        if query.query_text:
            conditions.append("(value LIKE ? OR tags LIKE ?)")
            like = f"%{query.query_text}%"
            params.extend([like, like])

        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        # S13: intelligent filters
        if query.memory_type:
            conditions.append("memory_type = ?")
            params.append(query.memory_type)

        if query.min_importance:
            min_rank = IMPORTANCE_RANK.get(query.min_importance, 0)
            valid_levels = [k for k, v in IMPORTANCE_RANK.items() if v >= min_rank]
            if valid_levels:
                placeholders = ",".join("?" for _ in valid_levels)
                conditions.append(f"importance IN ({placeholders})")
                params.extend(valid_levels)

        if query.confidence:
            conditions.append("confidence = ?")
            params.append(query.confidence)

        if query.lifecycle_status:
            conditions.append("lifecycle_status = ?")
            params.append(query.lifecycle_status)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = (
            f"SELECT key, value, tags, metadata FROM memories "
            f"WHERE {where} ORDER BY updated_at DESC LIMIT ?"
        )
        params.append(query.limit)

        rows = conn.execute(sql, params).fetchall()
        return [
            MemoryRecord(
                key=row["key"],
                value=json.loads(row["value"]),
                tags=json.loads(row["tags"]),
                metadata=json.loads(row["metadata"]),
            )
            for row in rows
        ]

    def replace(self, record: MemoryRecord) -> bool:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT metadata FROM memories WHERE key = ?", (record.key,)
        ).fetchone()
        if existing is None:
            return False

        now = datetime.now(timezone.utc).isoformat()
        old_meta = json.loads(existing["metadata"])
        meta = dict(record.metadata)
        meta["created_at"] = old_meta.get("created_at", now)
        meta["updated_at"] = now

        # S13: extract semantic fields
        mem_type = meta.get("memory_type", "fact")
        importance = meta.get("importance", "normal")
        confidence = meta.get("confidence", "explicit")
        lifecycle = meta.get("lifecycle_status", "active")
        provenance = meta.get("provenance", "")
        valid_from = meta.get("valid_from")
        valid_until = meta.get("valid_until")

        conn.execute(
            "UPDATE memories SET value = ?, tags = ?, metadata = ?, "
            "updated_at = ?, memory_type = ?, importance = ?, "
            "confidence = ?, lifecycle_status = ?, provenance = ?, "
            "valid_from = ?, valid_until = ? WHERE key = ?",
            (
                json.dumps(record.value),
                json.dumps(record.tags),
                json.dumps(meta),
                now,
                mem_type,
                importance,
                confidence,
                lifecycle,
                provenance,
                valid_from,
                valid_until,
                record.key,
            ),
        )
        conn.commit()
        return True

    def delete(self, key: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0
