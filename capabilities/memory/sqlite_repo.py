"""SQLite-backed MemoryRepository.

Uses only the Python standard-library `sqlite3` module.
No ORM, no external dependencies.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from capabilities.memory.repository import MemoryRepository
from core.contracts.memory import MemoryQuery, MemoryRecord
from core.log import get_logger

logger = get_logger(__name__)


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
        try:
            conn.execute(
                "INSERT INTO memories (key, value, tags, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.key,
                    json.dumps(record.value),
                    json.dumps(record.tags),
                    json.dumps(meta),
                    meta["created_at"],
                    now,
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug("Duplicate memory key: %s", record.key)
            return False

    def find(self, query: MemoryQuery) -> list[MemoryRecord]:
        conn = self._get_conn()
        conditions: list[str] = []
        params: list[object] = []

        if query.query_text:
            # Simple keyword matching against value and tags
            conditions.append("(value LIKE ? OR tags LIKE ?)")
            like = f"%{query.query_text}%"
            params.extend([like, like])

        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

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

        conn.execute(
            "UPDATE memories SET value = ?, tags = ?, metadata = ?, updated_at = ? WHERE key = ?",
            (
                json.dumps(record.value),
                json.dumps(record.tags),
                json.dumps(meta),
                now,
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
