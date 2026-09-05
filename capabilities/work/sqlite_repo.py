"""SQLite-backed WorkRepository — S17.

Uses only the Python standard-library sqlite3 module.
Complex nested objects (plan, steps, activity_log) are stored as a
JSON blob in the ``data`` column, following the same pattern as
SQLiteInvestigationRepository.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from capabilities.work.repository import WorkRepository
from core.contracts.work import (
    StepStatus,
    Work,
    WorkActivity,
    WorkActivityType,
    WorkPlan,
    WorkQuery,
    WorkStatus,
    WorkStep,
)
from core.log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _step_to_dict(s: WorkStep) -> dict:
    return {
        "step_id": s.step_id,
        "name": s.name,
        "description": s.description,
        "capability": s.capability,
        "input_payload": s.input_payload,
        "status": s.status.value,
        "dependencies": list(s.dependencies),
        "result": s.result,
        "error": s.error,
        "started_at": s.started_at,
        "completed_at": s.completed_at,
        "retry_count": s.retry_count,
        "max_retries": s.max_retries,
        "metadata": s.metadata,
    }


def _dict_to_step(d: dict) -> WorkStep:
    return WorkStep(
        step_id=d["step_id"],
        name=d["name"],
        description=d["description"],
        capability=d["capability"],
        input_payload=d.get("input_payload", {}),
        status=StepStatus(d.get("status", "pending")),
        dependencies=tuple(d.get("dependencies", ())),
        result=d.get("result", {}),
        error=d.get("error"),
        started_at=d.get("started_at"),
        completed_at=d.get("completed_at"),
        retry_count=d.get("retry_count", 0),
        max_retries=d.get("max_retries", 1),
        metadata=d.get("metadata", {}),
    )


def _plan_to_dict(p: WorkPlan) -> dict:
    return {
        "plan_id": p.plan_id,
        "steps": [_step_to_dict(s) for s in p.steps],
        "version": p.version,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "metadata": p.metadata,
    }


def _dict_to_plan(d: dict) -> WorkPlan:
    return WorkPlan(
        plan_id=d["plan_id"],
        steps=tuple(_dict_to_step(s) for s in d.get("steps", ())),
        version=d.get("version", 1),
        created_at=d.get("created_at", ""),
        updated_at=d.get("updated_at", ""),
        metadata=d.get("metadata", {}),
    )


def _activity_to_dict(a: WorkActivity) -> dict:
    return {
        "timestamp": a.timestamp,
        "activity_type": a.activity_type.value,
        "description": a.description,
        "step_id": a.step_id,
        "metadata": a.metadata,
    }


def _dict_to_activity(d: dict) -> WorkActivity:
    return WorkActivity(
        timestamp=d["timestamp"],
        activity_type=WorkActivityType(d.get("activity_type", "status_changed")),
        description=d.get("description", ""),
        step_id=d.get("step_id"),
        metadata=d.get("metadata", {}),
    )


def _work_to_data_blob(w: Work) -> str:
    payload: dict = {
        "activity_log": [_activity_to_dict(a) for a in w.activity_log],
        "metadata": w.metadata,
    }
    if w.plan is not None:
        payload["plan"] = _plan_to_dict(w.plan)
    return json.dumps(payload)


def _data_blob_to_fields(blob: str) -> dict:
    raw = json.loads(blob) if blob else {}
    fields: dict = {
        "activity_log": tuple(
            _dict_to_activity(a) for a in raw.get("activity_log", ())
        ),
        "metadata": raw.get("metadata", {}),
    }
    if "plan" in raw:
        fields["plan"] = _dict_to_plan(raw["plan"])
    return fields


def _row_to_work(row: sqlite3.Row) -> Work:
    nested = _data_blob_to_fields(row["data"])
    return Work(
        work_id=row["work_id"],
        objective=row["objective"],
        status=WorkStatus(row["status"]),
        current_step_id=row["current_step_id"],
        project_id=row["project_id"],
        goal_id=row["goal_id"],
        investigation_id=row["investigation_id"],
        tags=tuple(json.loads(row["tags"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        **nested,
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class SQLiteWorkRepository(WorkRepository):
    """Concrete repository persisting Work items in a local SQLite file."""

    def __init__(self, db_path: str | Path = "data/nav_work.db") -> None:
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS work (
                work_id          TEXT PRIMARY KEY,
                objective        TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'pending',
                current_step_id  TEXT,
                project_id       TEXT,
                goal_id          TEXT,
                investigation_id TEXT,
                tags             TEXT NOT NULL DEFAULT '[]',
                data             TEXT NOT NULL DEFAULT '{}',
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL
            )
            """
        )
        self._conn.commit()
        logger.info("SQLite work DB ready at %s", self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.initialize()
        assert self._conn is not None
        return self._conn

    def save(self, work: Work) -> bool:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        created = work.created_at or now
        updated = work.updated_at or now
        try:
            conn.execute(
                "INSERT INTO work "
                "(work_id, objective, status, current_step_id, "
                "project_id, goal_id, investigation_id, tags, "
                "data, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    work.work_id,
                    work.objective,
                    work.status.value,
                    work.current_step_id,
                    work.project_id,
                    work.goal_id,
                    work.investigation_id,
                    json.dumps(list(work.tags)),
                    _work_to_data_blob(work),
                    created,
                    updated,
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug("Duplicate work id: %s", work.work_id)
            return False

    def get(self, work_id: str) -> Work | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM work WHERE work_id = ?", (work_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_work(row)

    def find(self, query: WorkQuery) -> list[Work]:
        conn = self._get_conn()
        conditions: list[str] = []
        params: list[object] = []

        if query.query_text:
            conditions.append("(objective LIKE ? OR data LIKE ?)")
            like = f"%{query.query_text}%"
            params.extend([like, like])
        if query.status:
            conditions.append("status = ?")
            params.append(query.status)
        if query.project_id:
            conditions.append("project_id = ?")
            params.append(query.project_id)
        if query.goal_id:
            conditions.append("goal_id = ?")
            params.append(query.goal_id)
        if query.investigation_id:
            conditions.append("investigation_id = ?")
            params.append(query.investigation_id)
        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM work WHERE {where} ORDER BY updated_at DESC LIMIT ?"
        params.append(query.limit)
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_work(r) for r in rows]

    def update(self, work: Work) -> bool:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT work_id FROM work WHERE work_id = ?",
            (work.work_id,),
        ).fetchone()
        if existing is None:
            return False
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE work SET "
            "objective = ?, status = ?, current_step_id = ?, "
            "project_id = ?, goal_id = ?, investigation_id = ?, "
            "tags = ?, data = ?, updated_at = ? "
            "WHERE work_id = ?",
            (
                work.objective,
                work.status.value,
                work.current_step_id,
                work.project_id,
                work.goal_id,
                work.investigation_id,
                json.dumps(list(work.tags)),
                _work_to_data_blob(work),
                now,
                work.work_id,
            ),
        )
        conn.commit()
        return True

    def delete(self, work_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM work WHERE work_id = ?", (work_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
