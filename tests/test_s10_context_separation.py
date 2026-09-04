"""S10 tests: Memory vs context isolation."""

from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from capabilities.research.context_store import ResearchContextStore
from core.contracts.memory import MemoryQuery


class TestContextMemorySeparation:
    def test_research_context_not_in_memory(self, tmp_path) -> None:
        """Research session data must NOT appear in long-term memory."""
        store = ResearchContextStore()
        ctx = store.create("solid-state batteries")
        store.update(
            ctx.session_id,
            recent_findings=("Finding 1", "Finding 2"),
        )

        db_path = tmp_path / "test_memory.db"
        repo = SQLiteMemoryRepository(str(db_path))
        mem = MemoryService(repo)

        results = mem.retrieve(
            MemoryQuery(query_text="solid-state batteries")
        )
        assert len(results) == 0, (
            "Research context leaked into long-term memory!"
        )

    def test_explicit_memory_still_works(self, tmp_path) -> None:
        """Explicit memory storage must still function independently."""
        from core.contracts.memory import MemoryRecord

        db_path = tmp_path / "test_memory.db"
        repo = SQLiteMemoryRepository(str(db_path))
        mem = MemoryService(repo)

        record = MemoryRecord(
            key="explicit_001",
            value="Battery research for Project X",
            tags=["project", "battery"],
        )
        mem.store(record)

        results = mem.retrieve(MemoryQuery(query_text="Project X"))
        assert len(results) >= 1
        assert any("Project X" in r.value for r in results)
