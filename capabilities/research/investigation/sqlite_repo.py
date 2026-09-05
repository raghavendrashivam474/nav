"""SQLite-backed InvestigationRepository — S15 + S16.

Uses only the Python standard-library sqlite3 module.
Complex nested objects (findings, sources, evidence, hypotheses,
activity_log) are stored as a JSON blob in the ``data`` column.

S16: Added activity_log serialization (backward compatible —
old records without activity_log deserialize to an empty tuple).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from capabilities.research.investigation.models import (
    ActivityType,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationActivity,
    InvestigationQuery,
    InvestigationStatus,
)
from capabilities.research.investigation.repository import InvestigationRepository
from core.contracts.research import (
    ResearchEvidence,
    ResearchFinding,
    ResearchSource,
    SourceStatus,
    SourceType,
    SupportState,
)
from core.log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _source_to_dict(s: ResearchSource) -> dict:
    return {
        "source_id": s.source_id,
        "url": s.url,
        "canonical_url": s.canonical_url,
        "title": s.title,
        "source_type": s.source_type.value,
        "publisher": s.publisher,
        "status": s.status.value,
        "retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None,
        "error": s.error,
        "metadata": s.metadata,
    }


def _dict_to_source(d: dict) -> ResearchSource:
    return ResearchSource(
        source_id=d["source_id"],
        url=d["url"],
        canonical_url=d["canonical_url"],
        title=d["title"],
        source_type=SourceType(d.get("source_type", "other")),
        publisher=d.get("publisher"),
        status=SourceStatus(d.get("status", "discovered")),
        retrieved_at=(datetime.fromisoformat(d["retrieved_at"]) if d.get("retrieved_at") else None),
        error=d.get("error"),
        metadata=d.get("metadata", {}),
    )


def _evidence_to_dict(e: ResearchEvidence) -> dict:
    return {
        "evidence_id": e.evidence_id,
        "source_id": e.source_id,
        "claim": e.claim,
        "excerpt": e.excerpt,
        "relevance": e.relevance,
    }


def _dict_to_evidence(d: dict) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=d["evidence_id"],
        source_id=d["source_id"],
        claim=d["claim"],
        excerpt=d.get("excerpt", ""),
        relevance=d.get("relevance", "medium"),
    )


def _finding_to_dict(f: ResearchFinding) -> dict:
    return {
        "statement": f.statement,
        "evidence_ids": list(f.evidence_ids),
        "support": f.support.value,
        "notes": f.notes,
    }


def _dict_to_finding(d: dict) -> ResearchFinding:
    return ResearchFinding(
        statement=d["statement"],
        evidence_ids=tuple(d.get("evidence_ids", ())),
        support=SupportState(d.get("support", "insufficient")),
        notes=d.get("notes"),
    )


def _hypothesis_to_dict(h: Hypothesis) -> dict:
    return {
        "hypothesis_id": h.hypothesis_id,
        "statement": h.statement,
        "status": h.status.value,
        "evidence_ids": list(h.evidence_ids),
        "rationale": h.rationale,
        "created_at": h.created_at,
    }


def _dict_to_hypothesis(d: dict) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=d["hypothesis_id"],
        statement=d["statement"],
        status=HypothesisStatus(d.get("status", "proposed")),
        evidence_ids=tuple(d.get("evidence_ids", ())),
        rationale=d.get("rationale"),
        created_at=d.get("created_at", ""),
    )


def _activity_to_dict(a: InvestigationActivity) -> dict:
    return {
        "timestamp": a.timestamp,
        "activity_type": a.activity_type.value,
        "description": a.description,
        "metadata": a.metadata,
    }


def _dict_to_activity(d: dict) -> InvestigationActivity:
    return InvestigationActivity(
        timestamp=d["timestamp"],
        activity_type=ActivityType(d.get("activity_type", "research_conducted")),
        description=d.get("description", ""),
        metadata=d.get("metadata", {}),
    )


def _investigation_to_data_blob(inv: Investigation) -> str:
    """Serialise the complex nested fields into a JSON string."""
    payload = {
        "hypotheses": [_hypothesis_to_dict(h) for h in inv.hypotheses],
        "findings": [_finding_to_dict(f) for f in inv.findings],
        "conflicts": [_finding_to_dict(f) for f in inv.conflicts],
        "uncertainties": [_finding_to_dict(f) for f in inv.uncertainties],
        "sources": [_source_to_dict(s) for s in inv.sources],
        "evidence": [_evidence_to_dict(e) for e in inv.evidence],
        "open_questions": list(inv.open_questions),
        "metadata": inv.metadata,
        "activity_log": [_activity_to_dict(a) for a in inv.activity_log],
    }
    return json.dumps(payload)


def _data_blob_to_fields(blob: str) -> dict:
    """Deserialise the JSON data blob back into model objects."""
    raw = json.loads(blob) if blob else {}
    return {
        "hypotheses": tuple(_dict_to_hypothesis(h) for h in raw.get("hypotheses", ())),
        "findings": tuple(_dict_to_finding(f) for f in raw.get("findings", ())),
        "conflicts": tuple(_dict_to_finding(f) for f in raw.get("conflicts", ())),
        "uncertainties": tuple(_dict_to_finding(f) for f in raw.get("uncertainties", ())),
        "sources": tuple(_dict_to_source(s) for s in raw.get("sources", ())),
        "evidence": tuple(_dict_to_evidence(e) for e in raw.get("evidence", ())),
        "open_questions": tuple(raw.get("open_questions", ())),
        "metadata": raw.get("metadata", {}),
        "activity_log": tuple(
            _dict_to_activity(a) for a in raw.get("activity_log", ())
        ),
    }


def _row_to_investigation(row: sqlite3.Row) -> Investigation:
    """Reconstruct an Investigation from a database row."""
    nested = _data_blob_to_fields(row["data"])
    return Investigation(
        investigation_id=row["investigation_id"],
        title=row["title"],
        objective=row["objective"],
        status=InvestigationStatus(row["status"]),
        project_id=row["project_id"],
        goal_id=row["goal_id"],
        tags=tuple(json.loads(row["tags"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        **nested,
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class SQLiteInvestigationRepository(InvestigationRepository):
    """Concrete repository persisting investigations in a local SQLite file."""

    def __init__(self, db_path: str | Path = "data/nav_investigations.db") -> None:
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle --------------------------------------------------------

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                investigation_id TEXT PRIMARY KEY,
                title            TEXT NOT NULL,
                objective        TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'new',
                project_id       TEXT,
                goal_id          TEXT,
                tags             TEXT NOT NULL DEFAULT '[]',
                data             TEXT NOT NULL DEFAULT '{}',
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL
            )
            """
        )
        self._conn.commit()
        logger.info("SQLite investigation DB ready at %s", self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.initialize()
        assert self._conn is not None
        return self._conn

    # -- CRUD -------------------------------------------------------------

    def save(self, investigation: Investigation) -> bool:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        created = investigation.created_at or now
        updated = investigation.updated_at or now

        try:
            conn.execute(
                "INSERT INTO investigations "
                "(investigation_id, title, objective, status, "
                "project_id, goal_id, tags, data, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    investigation.investigation_id,
                    investigation.title,
                    investigation.objective,
                    investigation.status.value,
                    investigation.project_id,
                    investigation.goal_id,
                    json.dumps(list(investigation.tags)),
                    _investigation_to_data_blob(investigation),
                    created,
                    updated,
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug("Duplicate investigation id: %s", investigation.investigation_id)
            return False

    def get(self, investigation_id: str) -> Investigation | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM investigations WHERE investigation_id = ?",
            (investigation_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_investigation(row)

    def find(self, query: InvestigationQuery) -> list[Investigation]:
        conn = self._get_conn()
        conditions: list[str] = []
        params: list[object] = []

        if query.query_text:
            conditions.append("(title LIKE ? OR objective LIKE ? OR data LIKE ?)")
            like = f"%{query.query_text}%"
            params.extend([like, like, like])

        if query.status:
            conditions.append("status = ?")
            params.append(query.status)

        if query.project_id:
            conditions.append("project_id = ?")
            params.append(query.project_id)

        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM investigations WHERE {where} ORDER BY updated_at DESC LIMIT ?"
        params.append(query.limit)

        rows = conn.execute(sql, params).fetchall()
        return [_row_to_investigation(r) for r in rows]

    def update(self, investigation: Investigation) -> bool:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT investigation_id FROM investigations WHERE investigation_id = ?",
            (investigation.investigation_id,),
        ).fetchone()
        if existing is None:
            return False

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE investigations SET "
            "title = ?, objective = ?, status = ?, "
            "project_id = ?, goal_id = ?, tags = ?, "
            "data = ?, updated_at = ? "
            "WHERE investigation_id = ?",
            (
                investigation.title,
                investigation.objective,
                investigation.status.value,
                investigation.project_id,
                investigation.goal_id,
                json.dumps(list(investigation.tags)),
                _investigation_to_data_blob(investigation),
                now,
                investigation.investigation_id,
            ),
        )
        conn.commit()
        return True

    def delete(self, investigation_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM investigations WHERE investigation_id = ?",
            (investigation_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
