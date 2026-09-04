"""S10 tests: Research continuity resolver and context store."""

from capabilities.research.context_store import ResearchContextStore
from capabilities.research.continuity import ResearchContinuityResolver
from core.contracts.context import ResearchSessionContext
from core.contracts.research import ContinuationIntent


class TestContinuityResolver:
    def setup_method(self) -> None:
        self.resolver = ResearchContinuityResolver()
        self.ctx = ResearchSessionContext(
            session_id="test_001",
            root_query="solid-state batteries",
            open_questions=("manufacturing scalability",),
        )

    def test_no_context_returns_new(self) -> None:
        intent, topic = self.resolver.resolve("go deeper", None)
        assert intent == ContinuationIntent.NEW
        assert topic is None

    def test_deepen_go_deeper(self) -> None:
        intent, _ = self.resolver.resolve("Go deeper", self.ctx)
        assert intent == ContinuationIntent.DEEPEN

    def test_deepen_tell_me_more(self) -> None:
        intent, _ = self.resolver.resolve("Tell me more", self.ctx)
        assert intent == ContinuationIntent.DEEPEN

    def test_deepen_continue(self) -> None:
        intent, _ = self.resolver.resolve("continue", self.ctx)
        assert intent == ContinuationIntent.DEEPEN

    def test_focus_explicit(self) -> None:
        intent, topic = self.resolver.resolve("Focus on manufacturing", self.ctx)
        assert intent == ContinuationIntent.FOCUS
        assert topic is not None
        assert "manufacturing" in topic.lower()

    def test_focus_what_about(self) -> None:
        intent, topic = self.resolver.resolve("What about energy density?", self.ctx)
        assert intent == ContinuationIntent.FOCUS
        assert topic is not None
        assert "energy density" in topic.lower()

    def test_provenance_show_sources(self) -> None:
        intent, _ = self.resolver.resolve("Show me the sources", self.ctx)
        assert intent == ContinuationIntent.PROVENANCE

    def test_provenance_references(self) -> None:
        intent, _ = self.resolver.resolve("What are your references?", self.ctx)
        assert intent == ContinuationIntent.PROVENANCE

    def test_unrelated_query_returns_new(self) -> None:
        intent, _ = self.resolver.resolve("What is the weather today?", self.ctx)
        assert intent == ContinuationIntent.NEW

    def test_refine_deepen_uses_open_questions(self) -> None:
        query = self.resolver.refine_query("go deeper", ContinuationIntent.DEEPEN, None, self.ctx)
        assert "manufacturing scalability" in query.question
        assert query.depth == "deep"

    def test_refine_focus_sets_scope(self) -> None:
        query = self.resolver.refine_query(
            "focus on cost", ContinuationIntent.FOCUS, "cost", self.ctx
        )
        assert query.scope is not None
        assert "cost" in query.scope.lower()
        assert "solid-state batteries" in query.question

    def test_refine_provenance_zero_sources(self) -> None:
        query = self.resolver.refine_query(
            "show sources", ContinuationIntent.PROVENANCE, None, self.ctx
        )
        assert query.max_sources == 0

    def test_refine_new_ignores_context(self) -> None:
        query = self.resolver.refine_query(
            "quantum computing", ContinuationIntent.NEW, None, self.ctx
        )
        assert query.question == "quantum computing"


class TestContextStore:
    def setup_method(self) -> None:
        self.store = ResearchContextStore(ttl_seconds=60.0)

    def test_create_returns_context(self) -> None:
        ctx = self.store.create("test query")
        assert ctx.root_query == "test query"
        assert ctx.session_id.startswith("rs_")

    def test_get_returns_created(self) -> None:
        ctx = self.store.create("test")
        retrieved = self.store.get(ctx.session_id)
        assert retrieved is not None
        assert retrieved.root_query == "test"

    def test_get_missing_returns_none(self) -> None:
        assert self.store.get("nonexistent") is None

    def test_update_modifies_fields(self) -> None:
        ctx = self.store.create("test")
        updated = self.store.update(ctx.session_id, depth="deep", depth_level=2)
        assert updated is not None
        assert updated.depth == "deep"
        assert updated.depth_level == 2
        assert updated.root_query == "test"

    def test_remove_deletes_session(self) -> None:
        ctx = self.store.create("test")
        assert self.store.remove(ctx.session_id) is True
        assert self.store.get(ctx.session_id) is None

    def test_active_count(self) -> None:
        self.store.create("a")
        self.store.create("b")
        assert self.store.active_count == 2

    def test_expired_session_returns_none(self) -> None:
        store = ResearchContextStore(ttl_seconds=0.0)
        store.create("test")
        import time

        time.sleep(0.01)
        # Check active count or store retrieval triggers expiration
        store.cleanup_expired()
        assert store.active_count == 0

    def test_eviction_at_max(self) -> None:
        store = ResearchContextStore(max_sessions=2, ttl_seconds=3600)
        store.create("a")
        store.create("b")
        store.create("c")
        assert store.active_count == 2
