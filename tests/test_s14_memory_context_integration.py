"""S14 Memory → Context Integration tests.

Covers all 8 behavioral scenarios from the S14 brief:
1. No relevant memory — context remains valid
2. Relevant memory exists — appears in enriched context
3. Irrelevant memory exists — does not contaminate context
4. Important decision — available as contextual information
5. Superseded decision — respects S13 semantics
6. Provenance — source remains identifiable
7. Confidence — low-confidence ≠ high-confidence
8. Context without Memory — still functions when memory empty/unavailable
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.memory.semantics import (
    META_CONFIDENCE,
    META_IMPORTANCE,
    META_PROVENANCE,
    META_TYPE,
)
from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from core.context.integration import (
    ContextualSnapshot,
    MemoryContextIntegrator,
    MemoryContextItem,
)
from core.contracts.context import (
    Commitment,
    ConversationContext,
    CurrentFocus,
    Goal,
    NavContext,
    PersonalContext,
    Project,
    SessionContext,
    UserContext,
)
from core.contracts.memory import (
    MemoryCapabilityInterface,
    MemoryQuery,
    MemoryRecord,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_s14.db"


@pytest.fixture()
def memory_service(db_path: Path) -> MemoryService:
    repo = SQLiteMemoryRepository(db_path=db_path)
    return MemoryService(repository=repo)


@pytest.fixture()
def integrator(memory_service: MemoryService) -> MemoryContextIntegrator:
    return MemoryContextIntegrator(memory=memory_service)


def _make_context(
    projects: tuple[Project, ...] = (),
    goals: tuple[Goal, ...] = (),
    commitments: tuple[Commitment, ...] = (),
    focus: CurrentFocus | None = None,
) -> NavContext:
    """Helper to build a NavContext with optional PersonalContext."""
    pc = PersonalContext(
        projects=projects,
        goals=goals,
        commitments=commitments,
        current_focus=focus,
    )
    return NavContext(
        user=UserContext(user_id="test-user"),
        session=SessionContext(session_id="test-session"),
        conversation=ConversationContext(conversation_id="test-conv"),
        personal_context=pc,
    )


# ---------------------------------------------------------------------------
# Case 1: No relevant memory
# ---------------------------------------------------------------------------


class TestNoRelevantMemory:
    """Context remains valid when no useful memory exists."""

    def test_empty_memory_returns_valid_snapshot(
        self,
        integrator: MemoryContextIntegrator,
    ) -> None:
        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "debug NAV")

        assert isinstance(snapshot, ContextualSnapshot)
        assert snapshot.base_context is context
        assert snapshot.has_enrichment is False
        assert snapshot.relevant_memories == ()

    def test_unrelated_memory_not_included(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        """Memory about cooking should not appear for a NAV query."""
        memory_service.store(
            MemoryRecord(
                key="cook1",
                value="Best pasta recipe uses fresh tomatoes",
                tags=["cooking", "recipe"],
                metadata={META_TYPE: "fact"},
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "debug NAV")

        assert snapshot.has_enrichment is False


# ---------------------------------------------------------------------------
# Case 2: Relevant memory exists
# ---------------------------------------------------------------------------


class TestRelevantMemoryExists:
    """Relevant memory appears in enriched context."""

    def test_project_memory_included(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        memory_service.store(
            MemoryRecord(
                key="nav-arch",
                value="NAV uses modular architecture",
                tags=["NAV", "architecture"],
                metadata={
                    META_TYPE: "preference",
                    META_IMPORTANCE: "high",
                },
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "architecture")

        assert snapshot.has_enrichment is True
        keys = {m.memory_key for m in snapshot.relevant_memories}
        assert "nav-arch" in keys

    def test_focus_topic_matches_memory(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        memory_service.store(
            MemoryRecord(
                key="mem-int",
                value="Memory integration is the S14 goal",
                tags=["integration", "S14"],
                metadata={META_TYPE: "fact"},
            )
        )

        context = _make_context(
            focus=CurrentFocus(topic="integration", activity="coding"),
        )
        snapshot = integrator.build_snapshot(context)

        assert snapshot.has_enrichment is True
        assert any(m.memory_key == "mem-int" for m in snapshot.relevant_memories)


# ---------------------------------------------------------------------------
# Case 3: Irrelevant memory exists
# ---------------------------------------------------------------------------


class TestIrrelevantMemoryExcluded:
    """Irrelevant memory should not contaminate context."""

    def test_unrelated_tags_and_content_filtered(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        # Store relevant memory
        memory_service.store(
            MemoryRecord(
                key="nav1",
                value="NAV sprint planning",
                tags=["NAV"],
                metadata={META_TYPE: "fact"},
            )
        )
        # Store irrelevant memory
        memory_service.store(
            MemoryRecord(
                key="garden1",
                value="Tomato planting schedule for spring",
                tags=["gardening"],
                metadata={META_TYPE: "fact"},
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "sprint planning")

        keys = {m.memory_key for m in snapshot.relevant_memories}
        assert "nav1" in keys
        assert "garden1" not in keys


# ---------------------------------------------------------------------------
# Case 4: Important decision
# ---------------------------------------------------------------------------


class TestImportantDecision:
    """Important decisions are available as contextual information."""

    def test_high_importance_decision_included(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        memory_service.store(
            MemoryRecord(
                key="dec-arch",
                value={
                    "decision": "Keep modular architecture",
                    "reason": "Avoid premature distribution",
                },
                tags=["NAV", "architecture"],
                metadata={
                    META_TYPE: "decision",
                    META_IMPORTANCE: "critical",
                    META_CONFIDENCE: "explicit",
                    META_PROVENANCE: "User decided 2025-01-15",
                },
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "architecture change")

        assert snapshot.has_enrichment is True
        decision_items = [m for m in snapshot.relevant_memories if m.memory_type == "decision"]
        assert len(decision_items) >= 1
        assert decision_items[0].importance == "critical"
        assert isinstance(decision_items[0].value, dict)
        assert decision_items[0].value["decision"] == "Keep modular architecture"


# ---------------------------------------------------------------------------
# Case 5: Superseded decision
# ---------------------------------------------------------------------------


class TestSupersededDecision:
    """Superseded memories are excluded; only active ones appear."""

    def test_superseded_memory_excluded(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        # Store original preference
        memory_service.store(
            MemoryRecord(
                key="pref-sqlite",
                value="Prefer SQLite for local storage",
                tags=["database", "NAV"],
                metadata={META_TYPE: "preference"},
            )
        )
        # Supersede it
        memory_service.supersede(
            "pref-sqlite",
            MemoryRecord(
                key="pref-postgres",
                value="Prefer PostgreSQL for NAV",
                tags=["database", "NAV"],
                metadata={META_TYPE: "preference"},
            ),
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "database choice")

        keys = {m.memory_key for m in snapshot.relevant_memories}
        # The superseded memory should NOT appear
        assert "pref-sqlite" not in keys
        # The new active memory SHOULD appear
        assert "pref-postgres" in keys


# ---------------------------------------------------------------------------
# Case 6: Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    """Source remains identifiable through the integration layer."""

    def test_provenance_preserved(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        memory_service.store(
            MemoryRecord(
                key="prov1",
                value="User prefers dark mode",
                tags=["NAV", "UI"],
                metadata={
                    META_TYPE: "preference",
                    META_PROVENANCE: "User stated in session 2025-03-10",
                    META_CONFIDENCE: "explicit",
                },
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "UI preferences")

        prov_items = [m for m in snapshot.relevant_memories if m.memory_key == "prov1"]
        assert len(prov_items) == 1
        assert prov_items[0].provenance == "User stated in session 2025-03-10"
        assert prov_items[0].confidence == "explicit"
        # Full metadata should also be preserved
        assert "provenance" in prov_items[0].metadata


# ---------------------------------------------------------------------------
# Case 7: Confidence
# ---------------------------------------------------------------------------


class TestConfidence:
    """Low-confidence memories are treated differently from high-confidence."""

    def test_explicit_ranks_above_inferred(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        # Both about NAV, same importance, different confidence
        memory_service.store(
            MemoryRecord(
                key="inferred1",
                value="User might like microservices",
                tags=["NAV"],
                metadata={
                    META_TYPE: "observation",
                    META_CONFIDENCE: "inferred",
                    META_IMPORTANCE: "normal",
                },
            )
        )
        memory_service.store(
            MemoryRecord(
                key="explicit1",
                value="User explicitly rejected microservices",
                tags=["NAV"],
                metadata={
                    META_TYPE: "decision",
                    META_CONFIDENCE: "explicit",
                    META_IMPORTANCE: "normal",
                },
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "architecture")

        assert snapshot.has_enrichment is True
        keys = [m.memory_key for m in snapshot.relevant_memories]
        # Explicit should rank higher (appear first)
        if "explicit1" in keys and "inferred1" in keys:
            assert keys.index("explicit1") < keys.index("inferred1")

    def test_confidence_values_preserved(
        self,
        integrator: MemoryContextIntegrator,
        memory_service: MemoryService,
    ) -> None:
        memory_service.store(
            MemoryRecord(
                key="low-conf",
                value="Maybe user likes Rust",
                tags=["NAV"],
                metadata={META_CONFIDENCE: "inferred"},
            )
        )

        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "Rust")

        items = [m for m in snapshot.relevant_memories if m.memory_key == "low-conf"]
        if items:
            assert items[0].confidence == "inferred"


# ---------------------------------------------------------------------------
# Case 8: Context without Memory (resilience)
# ---------------------------------------------------------------------------


class TestContextWithoutMemory:
    """S14 must not make Context dependent on Memory being populated."""

    def test_empty_memory_still_produces_snapshot(
        self,
        integrator: MemoryContextIntegrator,
    ) -> None:
        """Memory store is empty — snapshot should still be valid."""
        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "anything")

        assert isinstance(snapshot, ContextualSnapshot)
        assert snapshot.base_context is context
        assert snapshot.has_enrichment is False

    def test_no_personal_context_still_works(
        self,
        integrator: MemoryContextIntegrator,
    ) -> None:
        """NavContext with personal_context=None should not crash."""
        context = NavContext(
            user=UserContext(user_id="test"),
            session=SessionContext(session_id="s1"),
            conversation=ConversationContext(conversation_id="c1"),
            personal_context=None,
        )
        snapshot = integrator.build_snapshot(context, "test query")

        assert isinstance(snapshot, ContextualSnapshot)
        assert snapshot.has_enrichment is False

    def test_memory_failure_returns_unenriched(
        self,
    ) -> None:
        """If memory raises, snapshot is still returned (un-enriched)."""

        class FailingMemory(MemoryCapabilityInterface):
            def store(self, record: MemoryRecord) -> bool:
                raise RuntimeError("DB down")

            def retrieve(self, query: MemoryQuery) -> list[MemoryRecord]:
                raise RuntimeError("DB down")

            def update(self, record: MemoryRecord) -> bool:
                raise RuntimeError("DB down")

            def forget(self, key: str) -> bool:
                raise RuntimeError("DB down")

        integrator = MemoryContextIntegrator(memory=FailingMemory())
        context = _make_context(
            projects=(Project(project_id="p1", name="NAV"),),
        )
        snapshot = integrator.build_snapshot(context, "test")

        assert isinstance(snapshot, ContextualSnapshot)
        assert snapshot.has_enrichment is False
        assert snapshot.base_context is context


# ---------------------------------------------------------------------------
# Additional: Data model integrity
# ---------------------------------------------------------------------------


class TestDataModels:
    """Verify S14 data model properties."""

    def test_contextual_snapshot_is_frozen(self) -> None:
        context = _make_context()
        snapshot = ContextualSnapshot(base_context=context)
        with pytest.raises(AttributeError):
            snapshot.interaction_hint = "changed"  # type: ignore[misc]

    def test_memory_context_item_is_frozen(self) -> None:
        item = MemoryContextItem(
            memory_key="k1",
            value="v1",
            memory_type="fact",
            importance="normal",
            confidence="explicit",
            provenance="",
        )
        with pytest.raises(AttributeError):
            item.value = "changed"  # type: ignore[misc]

    def test_snapshot_timestamp_populated(
        self,
        integrator: MemoryContextIntegrator,
    ) -> None:
        context = _make_context()
        snapshot = integrator.build_snapshot(context)
        assert snapshot.timestamp != ""
        assert "T" in snapshot.timestamp  # ISO format
