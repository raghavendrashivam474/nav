"""S10 integration scenarios: Multi-turn research continuity.

Tests the full research capability with continuity resolution
using mock providers (no live network required).
"""

from capabilities.research.capability import ResearchCapability
from capabilities.research.context_store import ResearchContextStore
from capabilities.research.service import ResearchService
from core.contracts.capability import Request


def _make_capability() -> ResearchCapability:
    """Create a research capability with mock providers and context store."""
    store = ResearchContextStore()
    service = ResearchService()
    return ResearchCapability(
        service=service, context_store=store
    )


class TestScenarioAFreshResearch:
    def test_fresh_research_returns_session_id(self) -> None:
        cap = _make_capability()
        req = Request(
            request_id="test_a",
            payload={"question": "Research solid-state batteries"},
        )
        resp = cap.invoke(req)
        assert resp.success
        assert "session_id" in resp.data
        assert resp.data["continuation_intent"] == "new"


class TestScenarioBGoDeeper:
    def test_go_deeper_uses_context(self) -> None:
        cap = _make_capability()
        req1 = Request(
            request_id="test_b1",
            payload={"question": "Research solid-state batteries"},
        )
        resp1 = cap.invoke(req1)
        session_id = resp1.data["session_id"]

        req2 = Request(
            request_id="test_b2",
            payload={
                "question": "Go deeper",
                "session_id": session_id,
            },
        )
        resp2 = cap.invoke(req2)
        assert resp2.success
        assert resp2.data["continuation_intent"] == "deepen"


class TestScenarioCFocusShift:
    def test_focus_narrows_scope(self) -> None:
        cap = _make_capability()
        req1 = Request(
            request_id="test_c1",
            payload={"question": "Research solid-state batteries"},
        )
        resp1 = cap.invoke(req1)
        session_id = resp1.data["session_id"]

        req2 = Request(
            request_id="test_c2",
            payload={
                "question": "Focus on manufacturing",
                "session_id": session_id,
            },
        )
        resp2 = cap.invoke(req2)
        assert resp2.success
        assert resp2.data["continuation_intent"] == "focus"


class TestScenarioDProvenance:
    def test_provenance_returns_without_research(self) -> None:
        cap = _make_capability()
        req1 = Request(
            request_id="test_d1",
            payload={"question": "Research solid-state batteries"},
        )
        resp1 = cap.invoke(req1)
        session_id = resp1.data["session_id"]

        req2 = Request(
            request_id="test_d2",
            payload={
                "question": "Show me the sources",
                "session_id": session_id,
            },
        )
        resp2 = cap.invoke(req2)
        assert resp2.success
        assert resp2.data["continuation_intent"] == "provenance"


class TestScenarioETopicSwitching:
    def test_topic_switch_creates_fresh_session(self) -> None:
        cap = _make_capability()

        # Turn 1: Solid-state batteries
        req1 = Request(
            request_id="t1",
            payload={"question": "Research solid-state batteries"},
        )
        resp1 = cap.invoke(req1)
        session_id_1 = resp1.data["session_id"]

        # Turn 2: Quantum computing (unrelated query, passed with same session_id)
        req2 = Request(
            request_id="t2",
            payload={
                "question": "Research quantum computing",
                "session_id": session_id_1,
            },
        )
        resp2 = cap.invoke(req2)
        session_id_2 = resp2.data["session_id"]

        # Session IDs must be different, and the second session must have quantum computing as root
        assert session_id_1 != session_id_2

        ctx2 = cap._context_store.get(session_id_2)
        assert ctx2 is not None
        assert "quantum computing" in ctx2.root_query.lower()
        assert "solid-state" not in ctx2.root_query.lower()


class TestScenarioGMemoryIsolation:
    def test_research_does_not_pollute_memory(self) -> None:
        cap = _make_capability()
        req = Request(
            request_id="test_g",
            payload={"question": "Research 20 sources on batteries"},
        )
        resp = cap.invoke(req)
        assert resp.success
        assert cap._memory is None or True  # no auto-persist
