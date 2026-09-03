"""S6 Cognition ↔ Memory integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.cognition.cognition import CognitionCapability
from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from core.contracts.capability import Request
from core.contracts.memory import MemoryQuery


@pytest.fixture()
def memory_service(tmp_path: Path) -> MemoryService:
    repo = SQLiteMemoryRepository(db_path=tmp_path / "cog_test.db")
    return MemoryService(repository=repo)


@pytest.fixture()
def cognition(memory_service: MemoryService) -> CognitionCapability:
    """Cognition with memory but NO AI gateway (stub mode)."""
    return CognitionCapability(gateway=None, memory=memory_service)


class TestCognitionMemoryIntegration:
    def test_remember_creates_memory(
        self, cognition: CognitionCapability, memory_service: MemoryService
    ):
        req = Request(
            request_id="c1",
            payload={"prompt": "Remember that I prefer Python for prototypes"},
        )
        resp = cognition.invoke(req)
        assert resp.success is True
        assert "Remembered" in resp.data["reply"]

        # Verify it's actually in the store
        results = memory_service.retrieve(MemoryQuery(query_text="Python"))
        assert len(results) == 1
        assert "Python" in results[0].value

    def test_forget_removes_memory(
        self, cognition: CognitionCapability, memory_service: MemoryService
    ):
        # First remember
        cognition.invoke(
            Request(
                request_id="c2",
                payload={"prompt": "Remember that SQLite is the backend"},
            )
        )
        assert len(memory_service.retrieve(MemoryQuery(query_text="SQLite"))) == 1

        # Now forget
        resp = cognition.invoke(
            Request(
                request_id="c3",
                payload={"prompt": "Forget that"},
            )
        )
        assert "Forgotten" in resp.data["reply"]
        assert len(memory_service.retrieve(MemoryQuery(query_text="SQLite"))) == 0

    def test_normal_prompt_still_works(self, cognition: CognitionCapability):
        req = Request(
            request_id="c4",
            payload={"prompt": "What is the capital of France?"},
        )
        resp = cognition.invoke(req)
        assert resp.success is True
        assert "Stub" in resp.data["reply"]  # stub mode, no gateway

    def test_memory_failure_doesnt_break_cognition(self, tmp_path: Path):
        """If memory is unavailable, cognition still works."""
        cog = CognitionCapability(gateway=None, memory=None)
        req = Request(request_id="c5", payload={"prompt": "Hello"})
        resp = cog.invoke(req)
        assert resp.success is True

    def test_backward_compatible_no_memory(self):
        """Existing code that creates CognitionCapability() still works."""
        cog = CognitionCapability()
        req = Request(request_id="c6", payload={"prompt": "test"})
        resp = cog.invoke(req)
        assert resp.success is True
