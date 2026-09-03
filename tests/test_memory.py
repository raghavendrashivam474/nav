"""S6 Memory tests — model, repository, service, capability, integration."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from capabilities.memory.capability import MemoryCapability
from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
from core.contracts.memory import MemoryQuery, MemoryRecord
from core.orchestration.orchestrator import Orchestrator

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_memory.db"


@pytest.fixture()
def repo(db_path: Path) -> SQLiteMemoryRepository:
    r = SQLiteMemoryRepository(db_path=db_path)
    r.initialize()
    return r


@pytest.fixture()
def service(repo: SQLiteMemoryRepository) -> MemoryService:
    return MemoryService(repository=repo)


@pytest.fixture()
def capability(service: MemoryService) -> MemoryCapability:
    return MemoryCapability(service=service)


def _make_record(
    key: str | None = None,
    value: str = "test memory",
    tags: list[str] | None = None,
    **meta,
) -> MemoryRecord:
    return MemoryRecord(
        key=key or f"test_{uuid.uuid4().hex[:8]}",
        value=value,
        tags=tags or ["test"],
        metadata=meta,
    )


# ======================================================================
# 1. MemoryRecord model
# ======================================================================


class TestMemoryRecord:
    def test_create_minimal(self):
        r = MemoryRecord(key="k1", value="hello")
        assert r.key == "k1"
        assert r.value == "hello"
        assert r.tags == []
        assert r.metadata == {}

    def test_create_full(self):
        r = MemoryRecord(
            key="k2",
            value="pref",
            tags=["preference", "user"],
            metadata={"importance": 0.9, "scope": "user"},
        )
        assert r.tags == ["preference", "user"]
        assert r.metadata["importance"] == 0.9

    def test_frozen(self):
        r = MemoryRecord(key="k", value="v")
        with pytest.raises(AttributeError):
            r.key = "other"  # type: ignore[misc]


# ======================================================================
# 2. SQLite Repository
# ======================================================================


class TestSQLiteRepository:
    def test_initialize_creates_db(self, db_path: Path):
        assert not db_path.exists()
        repo = SQLiteMemoryRepository(db_path=db_path)
        repo.initialize()
        assert db_path.exists()

    def test_initialize_idempotent(self, repo: SQLiteMemoryRepository):
        repo.save(_make_record(key="idem", value="v"))
        repo.initialize()  # should not destroy data
        results = repo.find(MemoryQuery(query_text="v"))
        assert len(results) == 1

    def test_save_and_find(self, repo: SQLiteMemoryRepository):
        rec = _make_record(key="s1", value="Python is great")
        assert repo.save(rec) is True
        results = repo.find(MemoryQuery(query_text="Python"))
        assert len(results) == 1
        assert results[0].value == "Python is great"

    def test_save_duplicate_returns_false(self, repo: SQLiteMemoryRepository):
        rec = _make_record(key="dup", value="v")
        assert repo.save(rec) is True
        assert repo.save(rec) is False

    def test_find_by_tag(self, repo: SQLiteMemoryRepository):
        repo.save(_make_record(key="t1", value="a", tags=["preference"]))
        repo.save(_make_record(key="t2", value="b", tags=["fact"]))
        results = repo.find(MemoryQuery(tags=["preference"]))
        assert len(results) == 1
        assert results[0].key == "t1"

    def test_find_limit(self, repo: SQLiteMemoryRepository):
        for i in range(5):
            repo.save(_make_record(key=f"lim{i}", value="same"))
        results = repo.find(MemoryQuery(query_text="same", limit=2))
        assert len(results) == 2

    def test_find_empty(self, repo: SQLiteMemoryRepository):
        results = repo.find(MemoryQuery(query_text="nothing"))
        assert results == []

    def test_replace(self, repo: SQLiteMemoryRepository):
        repo.save(_make_record(key="upd", value="old"))
        updated = _make_record(key="upd", value="new")
        assert repo.replace(updated) is True
        results = repo.find(MemoryQuery(query_text="new"))
        assert len(results) == 1
        assert results[0].value == "new"

    def test_replace_missing_returns_false(self, repo: SQLiteMemoryRepository):
        assert repo.replace(_make_record(key="ghost", value="v")) is False

    def test_delete(self, repo: SQLiteMemoryRepository):
        repo.save(_make_record(key="del1", value="gone"))
        assert repo.delete("del1") is True
        assert repo.find(MemoryQuery(query_text="gone")) == []

    def test_delete_missing_returns_false(self, repo: SQLiteMemoryRepository):
        assert repo.delete("nope") is False

    def test_metadata_preserved(self, repo: SQLiteMemoryRepository):
        rec = _make_record(key="meta1", value="v", importance=0.9, scope="user")
        repo.save(rec)
        results = repo.find(MemoryQuery(query_text="v"))
        assert results[0].metadata["importance"] == 0.9
        assert results[0].metadata["scope"] == "user"
        assert "created_at" in results[0].metadata
        assert "updated_at" in results[0].metadata


# ======================================================================
# 3. Memory Service
# ======================================================================


class TestMemoryService:
    def test_store_and_retrieve(self, service: MemoryService):
        rec = _make_record(key="svc1", value="service test")
        assert service.store(rec) is True
        results = service.retrieve(MemoryQuery(query_text="service"))
        assert len(results) == 1

    def test_update(self, service: MemoryService):
        service.store(_make_record(key="svc2", value="before"))
        service.update(_make_record(key="svc2", value="after"))
        results = service.retrieve(MemoryQuery(query_text="after"))
        assert len(results) == 1

    def test_forget(self, service: MemoryService):
        service.store(_make_record(key="svc3", value="temp"))
        assert service.forget("svc3") is True
        assert service.retrieve(MemoryQuery(query_text="temp")) == []

    def test_is_memory_request(self):
        assert MemoryService.is_memory_request("Remember that I like Python")
        assert MemoryService.is_memory_request("please remember this")
        assert MemoryService.is_memory_request("keep in mind that S6 is done")
        assert not MemoryService.is_memory_request("What is Python?")

    def test_extract_memory_content(self):
        assert (
            MemoryService.extract_memory_content("Remember that I like Python") == "I like Python"
        )
        assert MemoryService.extract_memory_content("Remember S6 uses SQLite") == "S6 uses SQLite"

    def test_is_forget_request(self):
        assert MemoryService.is_forget_request("Forget that")
        assert MemoryService.is_forget_request("please forget this")
        assert not MemoryService.is_forget_request("Remember this")


# ======================================================================
# 4. Memory Capability (via Orchestrator)
# ======================================================================


class TestMemoryCapability:
    def test_capability_metadata(self, capability: MemoryCapability):
        assert capability.name == "memory"
        assert capability.version == "0.1.0"

    def test_store_via_invoke(self, capability: MemoryCapability):
        req = Request(
            request_id="r1",
            payload={
                "action": "store",
                "key": "cap1",
                "value": "capability test",
                "tags": ["test"],
            },
        )
        resp = capability.invoke(req)
        assert resp.success is True
        assert resp.data["stored"] is True

    def test_retrieve_via_invoke(self, capability: MemoryCapability):
        capability.store(_make_record(key="cap2", value="find me"))
        req = Request(
            request_id="r2",
            payload={"action": "retrieve", "query_text": "find me"},
        )
        resp = capability.invoke(req)
        assert resp.success is True
        assert len(resp.data["memories"]) == 1

    def test_forget_via_invoke(self, capability: MemoryCapability):
        capability.store(_make_record(key="cap3", value="delete me"))
        req = Request(
            request_id="r3",
            payload={"action": "forget", "key": "cap3"},
        )
        resp = capability.invoke(req)
        assert resp.success is True
        assert resp.data["forgotten"] is True

    def test_unknown_action(self, capability: MemoryCapability):
        req = Request(request_id="r4", payload={"action": "dance"})
        resp = capability.invoke(req)
        assert resp.success is False

    def test_missing_field(self, capability: MemoryCapability):
        req = Request(request_id="r5", payload={"action": "store"})
        resp = capability.invoke(req)
        assert resp.success is False

    def test_orchestrator_routing(self, capability: MemoryCapability):
        registry = CapabilityRegistry()
        registry.register(capability)
        orch = Orchestrator(registry)
        req = Request(
            request_id="r6",
            payload={"action": "store", "key": "orch1", "value": "routed"},
        )
        resp = orch.route_request("memory", req)
        assert resp.success is True


# ======================================================================
# 5. Cross-process persistence
# ======================================================================


class TestCrossProcessPersistence:
    def test_persist_across_reopen(self, db_path: Path):
        """Store in one repo instance, retrieve in a completely new one."""
        repo_a = SQLiteMemoryRepository(db_path=db_path)
        repo_a.initialize()
        repo_a.save(_make_record(key="persist1", value="I survive restarts"))
        del repo_a  # simulate shutdown

        repo_b = SQLiteMemoryRepository(db_path=db_path)
        repo_b.initialize()
        results = repo_b.find(MemoryQuery(query_text="survive"))
        assert len(results) == 1
        assert results[0].value == "I survive restarts"
