"""S13 Memory Intelligence tests.

Covers: semantics, schema migration, intelligent store/retrieve,
supersede lifecycle, contradiction detection, decision memory,
and backward compatibility with S6-S12 memory behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.memory.semantics import (
    META_CONFIDENCE,
    META_IMPORTANCE,
    META_LIFECYCLE,
    META_PROVENANCE,
    META_SUPERSEDED_BY,
    META_SUPERSEDES,
    META_TYPE,
    Confidence,
    Importance,
    LifecycleStatus,
    MemoryType,
    apply_defaults,
)
from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from core.contracts.memory import MemoryQuery, MemoryRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_s13.db"


@pytest.fixture()
def service(db_path: Path) -> MemoryService:
    repo = SQLiteMemoryRepository(db_path=db_path)
    return MemoryService(repository=repo)


# ---------------------------------------------------------------------------
# Semantics Unit Tests
# ---------------------------------------------------------------------------


class TestSemantics:
    def test_memory_type_values(self) -> None:
        assert MemoryType.FACT.value == "fact"
        assert MemoryType.DECISION.value == "decision"
        assert MemoryType.PREFERENCE.value == "preference"

    def test_importance_values(self) -> None:
        assert Importance.LOW.value == "low"
        assert Importance.CRITICAL.value == "critical"

    def test_confidence_values(self) -> None:
        assert Confidence.EXPLICIT.value == "explicit"
        assert Confidence.INFERRED.value == "inferred"

    def test_lifecycle_values(self) -> None:
        assert LifecycleStatus.ACTIVE.value == "active"
        assert LifecycleStatus.SUPERSEDED.value == "superseded"
        assert LifecycleStatus.ARCHIVED.value == "archived"

    def test_apply_defaults_empty(self) -> None:
        meta = apply_defaults({})
        assert meta[META_TYPE] == "fact"
        assert meta[META_IMPORTANCE] == "normal"
        assert meta[META_CONFIDENCE] == "explicit"
        assert meta[META_LIFECYCLE] == "active"
        assert meta[META_PROVENANCE] == ""

    def test_apply_defaults_preserves_existing(self) -> None:
        meta = apply_defaults({
            META_TYPE: "decision",
            META_IMPORTANCE: "critical",
            "custom_key": "custom_value",
        })
        assert meta[META_TYPE] == "decision"
        assert meta[META_IMPORTANCE] == "critical"
        assert meta[META_CONFIDENCE] == "explicit"  # default filled
        assert meta["custom_key"] == "custom_value"  # preserved


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    """Existing S6-S12 code must continue to work unchanged."""

    def test_store_plain_record(self, service: MemoryService) -> None:
        record = MemoryRecord(key="k1", value="hello")
        assert service.store(record) is True

    def test_retrieve_plain_record(self, service: MemoryService) -> None:
        service.store(MemoryRecord(key="k1", value="hello world"))
        results = service.retrieve(MemoryQuery(query_text="hello"))
        assert len(results) == 1
        assert results[0].key == "k1"

    def test_update_plain_record(self, service: MemoryService) -> None:
        service.store(MemoryRecord(key="k1", value="v1"))
        assert service.update(MemoryRecord(key="k1", value="v2")) is True
        results = service.retrieve(MemoryQuery(query_text="v2"))
        assert len(results) == 1

    def test_forget_plain_record(self, service: MemoryService) -> None:
        service.store(MemoryRecord(key="k1", value="v1"))
        assert service.forget("k1") is True
        assert service.retrieve(MemoryQuery(query_text="v1")) == []

    def test_duplicate_key_returns_false(self, service: MemoryService) -> None:
        service.store(MemoryRecord(key="k1", value="v1"))
        assert service.store(MemoryRecord(key="k1", value="v2")) is False

    def test_old_style_query_still_works(self, service: MemoryService) -> None:
        """MemoryQuery with only query_text/tags/limit must work."""
        service.store(MemoryRecord(key="k1", value="test", tags=["a"]))
        q = MemoryQuery(query_text="test", tags=["a"], limit=5)
        assert len(service.retrieve(q)) == 1

    def test_semantics_auto_applied(self, service: MemoryService) -> None:
        """Even plain records get semantic defaults in metadata."""
        service.store(MemoryRecord(key="k1", value="v1"))
        results = service.retrieve(MemoryQuery(query_text="v1"))
        meta = results[0].metadata
        assert meta[META_TYPE] == "fact"
        assert meta[META_IMPORTANCE] == "normal"
        assert meta[META_CONFIDENCE] == "explicit"
        assert meta[META_LIFECYCLE] == "active"


# ---------------------------------------------------------------------------
# Intelligent Store & Retrieve
# ---------------------------------------------------------------------------


class TestIntelligentStoreRetrieve:
    def test_store_with_explicit_semantics(self, service: MemoryService) -> None:
        record = MemoryRecord(
            key="d1",
            value="Use PostgreSQL",
            tags=["architecture", "database"],
            metadata={
                META_TYPE: MemoryType.DECISION.value,
                META_IMPORTANCE: Importance.HIGH.value,
                META_CONFIDENCE: Confidence.EXPLICIT.value,
                META_PROVENANCE: "User stated in conversation",
            },
        )
        assert service.store(record) is True
        results = service.retrieve(MemoryQuery(query_text="PostgreSQL"))
        assert len(results) == 1
        assert results[0].metadata[META_TYPE] == "decision"
        assert results[0].metadata[META_IMPORTANCE] == "high"

    def test_filter_by_memory_type(self, service: MemoryService) -> None:
        service.store(MemoryRecord(
            key="f1", value="Python 3.13",
            metadata={META_TYPE: "fact"},
        ))
        service.store(MemoryRecord(
            key="d1", value="Use async",
            metadata={META_TYPE: "decision"},
        ))
        results = service.retrieve(MemoryQuery(memory_type="decision"))
        assert len(results) == 1
        assert results[0].key == "d1"

    def test_filter_by_min_importance(self, service: MemoryService) -> None:
        service.store(MemoryRecord(
            key="low1", value="trivial",
            metadata={META_IMPORTANCE: "low"},
        ))
        service.store(MemoryRecord(
            key="high1", value="critical thing",
            metadata={META_IMPORTANCE: "high"},
        ))
        service.store(MemoryRecord(
            key="crit1", value="most important",
            metadata={META_IMPORTANCE: "critical"},
        ))
        results = service.retrieve(MemoryQuery(min_importance="high"))
        keys = {r.key for r in results}
        assert "high1" in keys
        assert "crit1" in keys
        assert "low1" not in keys

    def test_filter_by_confidence(self, service: MemoryService) -> None:
        service.store(MemoryRecord(
            key="e1", value="explicit fact",
            metadata={META_CONFIDENCE: "explicit"},
        ))
        service.store(MemoryRecord(
            key="i1", value="inferred thing",
            metadata={META_CONFIDENCE: "inferred"},
        ))
        results = service.retrieve(MemoryQuery(confidence="inferred"))
        assert len(results) == 1
        assert results[0].key == "i1"

    def test_filter_by_lifecycle(self, service: MemoryService) -> None:
        service.store(MemoryRecord(
            key="a1", value="active",
            metadata={META_LIFECYCLE: "active"},
        ))
        service.store(MemoryRecord(
            key="s1", value="superseded",
            metadata={META_LIFECYCLE: "superseded"},
        ))
        active = service.retrieve(MemoryQuery(lifecycle_status="active"))
        assert all(r.key == "a1" for r in active)
        superseded = service.retrieve(MemoryQuery(lifecycle_status="superseded"))
        assert all(r.key == "s1" for r in superseded)

    def test_combined_filters(self, service: MemoryService) -> None:
        service.store(MemoryRecord(
            key="d1", value="decision A",
            metadata={META_TYPE: "decision", META_IMPORTANCE: "high"},
        ))
        service.store(MemoryRecord(
            key="d2", value="decision B",
            metadata={META_TYPE: "decision", META_IMPORTANCE: "low"},
        ))
        service.store(MemoryRecord(
            key="f1", value="fact C",
            metadata={META_TYPE: "fact", META_IMPORTANCE: "high"},
        ))
        results = service.retrieve(MemoryQuery(
            memory_type="decision", min_importance="high"
        ))
        assert len(results) == 1
        assert results[0].key == "d1"


# ---------------------------------------------------------------------------
# Supersede Lifecycle
# ---------------------------------------------------------------------------


class TestSupersede:
    def test_supersede_marks_old_and_creates_new(
        self, service: MemoryService
    ) -> None:
        service.store(MemoryRecord(
            key="pref1", value="prefer SQLite",
            tags=["database"],
            metadata={META_TYPE: "preference"},
        ))
        new = MemoryRecord(
            key="pref2", value="prefer PostgreSQL",
            tags=["database"],
            metadata={META_TYPE: "preference"},
        )
        assert service.supersede("pref1", new) is True

        # Old should be superseded
        active = service.retrieve(MemoryQuery(lifecycle_status="active"))
        assert all(r.key != "pref1" for r in active)

        superseded = service.retrieve(MemoryQuery(lifecycle_status="superseded"))
        assert len(superseded) == 1
        assert superseded[0].key == "pref1"
        assert superseded[0].metadata[META_SUPERSEDED_BY] == "pref2"

        # New should link back to old
        new_results = service.retrieve(MemoryQuery(query_text="PostgreSQL"))
        assert len(new_results) == 1
        assert new_results[0].metadata[META_SUPERSEDES] == "pref1"

    def test_supersede_nonexistent_returns_false(
        self, service: MemoryService
    ) -> None:
        new = MemoryRecord(key="new1", value="v")
        assert service.supersede("nonexistent", new) is False

    def test_supersede_preserves_history(
        self, service: MemoryService
    ) -> None:
        """Decision evolution: old decisions are not lost."""
        service.store(MemoryRecord(
            key="d1", value="Use REST",
            metadata={META_TYPE: "decision"},
        ))
        service.supersede("d1", MemoryRecord(
            key="d2", value="Use GraphQL",
            metadata={META_TYPE: "decision"},
        ))
        service.supersede("d2", MemoryRecord(
            key="d3", value="Use tRPC",
            metadata={META_TYPE: "decision"},
        ))
        # All three exist in the database
        all_decisions = service.retrieve(MemoryQuery(
            memory_type="decision", limit=10
        ))
        # Only d3 is active (default filter not applied, so all returned)
        active = [r for r in all_decisions
                  if r.metadata.get(META_LIFECYCLE) == "active"]
        assert len(active) == 1
        assert active[0].key == "d3"

        # But superseded ones are still retrievable
        superseded = [r for r in all_decisions
                      if r.metadata.get(META_LIFECYCLE) == "superseded"]
        assert len(superseded) == 2


# ---------------------------------------------------------------------------
# Contradiction Detection
# ---------------------------------------------------------------------------


class TestContradictions:
    def test_detects_contradiction(self, service: MemoryService) -> None:
        service.store(MemoryRecord(
            key="p1", value="prefer local AI",
            tags=["ai", "preference"],
            metadata={META_TYPE: "preference"},
        ))
        candidate = MemoryRecord(
            key="p2", value="prefer cloud AI",
            tags=["ai", "preference"],
            metadata={META_TYPE: "preference"},
        )
        contradictions = service.detect_contradictions(candidate)
        assert len(contradictions) == 1
        assert contradictions[0].key == "p1"

    def test_no_contradiction_different_types(
        self, service: MemoryService
    ) -> None:
        service.store(MemoryRecord(
            key="f1", value="local AI",
            tags=["ai"],
            metadata={META_TYPE: "fact"},
        ))
        candidate = MemoryRecord(
            key="p1", value="cloud AI",
            tags=["ai"],
            metadata={META_TYPE: "preference"},
        )
        assert service.detect_contradictions(candidate) == []

    def test_no_contradiction_same_value(
        self, service: MemoryService
    ) -> None:
        service.store(MemoryRecord(
            key="p1", value="prefer local AI",
            tags=["ai"],
            metadata={META_TYPE: "preference"},
        ))
        candidate = MemoryRecord(
            key="p2", value="prefer local AI",
            tags=["ai"],
            metadata={META_TYPE: "preference"},
        )
        assert service.detect_contradictions(candidate) == []

    def test_no_contradiction_no_tag_overlap(
        self, service: MemoryService
    ) -> None:
        service.store(MemoryRecord(
            key="p1", value="local",
            tags=["ai"],
            metadata={META_TYPE: "preference"},
        ))
        candidate = MemoryRecord(
            key="p2", value="cloud",
            tags=["database"],
            metadata={META_TYPE: "preference"},
        )
        assert service.detect_contradictions(candidate) == []


# ---------------------------------------------------------------------------
# Decision Memory Foundation
# ---------------------------------------------------------------------------


class TestDecisionMemory:
    def test_structured_decision_value(self, service: MemoryService) -> None:
        """Decisions can carry structured reasoning in value (Any/JSON)."""
        decision = MemoryRecord(
            key="dec-postgres-2026",
            value={
                "decision": "Use PostgreSQL",
                "reason": "minimize infrastructure",
                "alternatives": ["SQLite", "MongoDB"],
            },
            tags=["architecture", "database"],
            metadata={
                META_TYPE: "decision",
                META_IMPORTANCE: "high",
                META_CONFIDENCE: "explicit",
                META_PROVENANCE: "User stated 2026-09-05",
            },
        )
        assert service.store(decision) is True
        results = service.retrieve(MemoryQuery(query_text="PostgreSQL"))
        assert len(results) == 1
        val = results[0].value
        assert isinstance(val, dict)
        assert val["decision"] == "Use PostgreSQL"
        assert val["reason"] == "minimize infrastructure"

    def test_inference_stays_inferred(self, service: MemoryService) -> None:
        """NAV must never silently turn an inference into a fact."""
        inferred = MemoryRecord(
            key="inf1",
            value="User might prefer simplicity",
            metadata={
                META_TYPE: "observation",
                META_CONFIDENCE: "inferred",
            },
        )
        service.store(inferred)
        results = service.retrieve(MemoryQuery(query_text="simplicity"))
        assert results[0].metadata[META_CONFIDENCE] == "inferred"
        # Explicit filter should NOT return this
        explicit_only = service.retrieve(MemoryQuery(confidence="explicit"))
        assert all(r.key != "inf1" for r in explicit_only)


# ---------------------------------------------------------------------------
# Temporal Semantics
# ---------------------------------------------------------------------------


class TestTemporalSemantics:
    def test_valid_from_until_stored(self, service: MemoryService) -> None:
        record = MemoryRecord(
            key="t1",
            value="Working on project X",
            metadata={
                "valid_from": "2025-01-01",
                "valid_until": "2025-12-31",
            },
        )
        service.store(record)
        results = service.retrieve(MemoryQuery(query_text="project X"))
        assert results[0].metadata["valid_from"] == "2025-01-01"
        assert results[0].metadata["valid_until"] == "2025-12-31"


# ---------------------------------------------------------------------------
# S6 Regex Helpers (Regression)
# ---------------------------------------------------------------------------


class TestRegexHelpers:
    def test_is_memory_request(self) -> None:
        assert MemoryService.is_memory_request("remember that I like Python")
        assert MemoryService.is_memory_request("keep in mind I use Linux")
        assert not MemoryService.is_memory_request("what is Python?")

    def test_extract_memory_content(self) -> None:
        assert MemoryService.extract_memory_content(
            "remember that I like Python"
        ) == "I like Python"

    def test_is_forget_request(self) -> None:
        assert MemoryService.is_forget_request("forget that I like Python")
        assert not MemoryService.is_forget_request("remember this")
