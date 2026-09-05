"""Comprehensive test suite for S15 — Research Partner (Investigations)."""

from __future__ import annotations

from pathlib import Path

from capabilities.research.investigation.models import (
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationQuery,
    InvestigationStatus,
)
from capabilities.research.investigation.service import InvestigationService
from capabilities.research.investigation.sqlite_repo import (
    SQLiteInvestigationRepository,
)
from core.contracts.context import (
    ConversationContext,
    CurrentFocus,
    NavContext,
    PersonalContext,
    Project,
    SessionContext,
    UserContext,
)
from core.contracts.research import (
    ResearchEvidence,
    ResearchFinding,
    ResearchQuery,
    ResearchResult,
    ResearchSource,
    SourceStatus,
    SourceType,
    SupportState,
)

# ---------------------------------------------------------------------------
# Fake ResearchService for testing conduct_research
# ---------------------------------------------------------------------------


class FakeResearchService:
    """Deterministic stand-in for ResearchService.execute_research."""

    def __init__(self) -> None:
        self.calls: list[ResearchQuery] = []

    def execute_research(self, query: ResearchQuery) -> ResearchResult:
        self.calls.append(query)
        s1 = ResearchSource(
            source_id="src_fake_1",
            url="https://example.com/paper1",
            canonical_url="https://example.com/paper1",
            title="Fake Paper 1",
            source_type=SourceType.PAPER,
            status=SourceStatus.RETRIEVED,
        )
        e1 = ResearchEvidence(
            evidence_id="ev_fake_1",
            source_id="src_fake_1",
            claim="Fake claim about the topic",
            excerpt="some excerpt",
            relevance="high",
        )
        f1 = ResearchFinding(
            statement="The topic has significant implications.",
            evidence_ids=("ev_fake_1",),
            support=SupportState.SUPPORTED,
        )
        return ResearchResult(
            query=query,
            sources=(s1,),
            evidence=(e1,),
            findings=(f1,),
            open_questions=("What are the long-term effects?",),
        )


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestInvestigationModels:
    def test_investigation_defaults(self):
        inv = Investigation(
            investigation_id="inv_1",
            title="Test",
            objective="Learn about X",
        )
        assert inv.status == InvestigationStatus.NEW
        assert inv.hypotheses == ()
        assert inv.findings == ()
        assert inv.sources == ()
        assert inv.evidence == ()
        assert inv.open_questions == ()
        assert inv.tags == ()
        assert inv.project_id is None

    def test_investigation_helper_sources_by_status(self):
        s1 = ResearchSource(
            source_id="s1",
            url="https://a.com",
            canonical_url="https://a.com",
            title="A",
            status=SourceStatus.RETRIEVED,
        )
        s2 = ResearchSource(
            source_id="s2",
            url="https://b.com",
            canonical_url="https://b.com",
            title="B",
            status=SourceStatus.FAILED,
        )
        inv = Investigation(
            investigation_id="inv_1",
            title="T",
            objective="O",
            sources=(s1, s2),
        )
        assert len(inv.sources_by_status(SourceStatus.RETRIEVED)) == 1
        assert len(inv.sources_by_status(SourceStatus.FAILED)) == 1

    def test_investigation_helper_evidence_for_source(self):
        e1 = ResearchEvidence(evidence_id="e1", source_id="s1", claim="C1")
        e2 = ResearchEvidence(evidence_id="e2", source_id="s2", claim="C2")
        inv = Investigation(
            investigation_id="inv_1",
            title="T",
            objective="O",
            evidence=(e1, e2),
        )
        assert len(inv.evidence_for_source("s1")) == 1
        assert inv.evidence_for_source("s1")[0].claim == "C1"

    def test_investigation_helper_evidence_for_finding(self):
        e1 = ResearchEvidence(evidence_id="e1", source_id="s1", claim="C1")
        e2 = ResearchEvidence(evidence_id="e2", source_id="s1", claim="C2")
        f = ResearchFinding(statement="Finding", evidence_ids=("e1",))
        inv = Investigation(
            investigation_id="inv_1",
            title="T",
            objective="O",
            evidence=(e1, e2),
            findings=(f,),
        )
        matched = inv.evidence_for_finding(f)
        assert len(matched) == 1
        assert matched[0].evidence_id == "e1"

    def test_hypothesis_defaults(self):
        h = Hypothesis(hypothesis_id="h1", statement="X causes Y")
        assert h.status == HypothesisStatus.PROPOSED
        assert h.evidence_ids == ()

    def test_investigation_query_defaults(self):
        q = InvestigationQuery()
        assert q.query_text is None
        assert q.limit == 20


# ---------------------------------------------------------------------------
# Repository round-trip tests
# ---------------------------------------------------------------------------


class TestInvestigationRepository:
    def test_save_and_get(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(
            investigation_id="inv_rt1",
            title="Round-trip test",
            objective="Verify persistence",
            tags=("test", "s15"),
        )
        assert repo.save(inv) is True
        loaded = repo.get("inv_rt1")
        assert loaded is not None
        assert loaded.title == "Round-trip test"
        assert loaded.tags == ("test", "s15")
        assert loaded.status == InvestigationStatus.NEW

    def test_save_duplicate_returns_false(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(investigation_id="inv_dup", title="T", objective="O")
        assert repo.save(inv) is True
        assert repo.save(inv) is False

    def test_get_missing_returns_none(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        assert repo.get("nonexistent") is None

    def test_update(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(investigation_id="inv_upd", title="T", objective="O")
        repo.save(inv)
        from dataclasses import replace

        updated = replace(inv, status=InvestigationStatus.ACTIVE)
        assert repo.update(updated) is True
        loaded = repo.get("inv_upd")
        assert loaded is not None
        assert loaded.status == InvestigationStatus.ACTIVE

    def test_update_missing_returns_false(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(investigation_id="inv_ghost", title="T", objective="O")
        assert repo.update(inv) is False

    def test_delete(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(investigation_id="inv_del", title="T", objective="O")
        repo.save(inv)
        assert repo.delete("inv_del") is True
        assert repo.get("inv_del") is None
        assert repo.delete("inv_del") is False

    def test_find_by_status(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        from dataclasses import replace

        inv1 = Investigation(investigation_id="inv_f1", title="A", objective="O")
        inv2 = replace(
            Investigation(investigation_id="inv_f2", title="B", objective="O"),
            status=InvestigationStatus.ACTIVE,
        )
        repo.save(inv1)
        repo.save(inv2)

        results = repo.find(InvestigationQuery(status="active"))
        assert len(results) == 1
        assert results[0].investigation_id == "inv_f2"

    def test_find_by_text(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(
            investigation_id="inv_ft",
            title="Solid-state batteries",
            objective="Investigate electrolyte interfaces",
        )
        repo.save(inv)
        results = repo.find(InvestigationQuery(query_text="electrolyte"))
        assert len(results) == 1

    def test_find_by_project(self, tmp_path: Path):
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        inv = Investigation(
            investigation_id="inv_fp",
            title="T",
            objective="O",
            project_id="proj_1",
        )
        repo.save(inv)
        results = repo.find(InvestigationQuery(project_id="proj_1"))
        assert len(results) == 1

    def test_round_trip_complex_data(self, tmp_path: Path):
        """Ensure nested findings, sources, evidence, hypotheses survive."""
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()
        s = ResearchSource(
            source_id="s1",
            url="https://x.com",
            canonical_url="https://x.com",
            title="X",
            source_type=SourceType.PAPER,
            status=SourceStatus.RETRIEVED,
        )
        e = ResearchEvidence(evidence_id="e1", source_id="s1", claim="Claim")
        f = ResearchFinding(
            statement="Finding",
            evidence_ids=("e1",),
            support=SupportState.SUPPORTED,
        )
        h = Hypothesis(
            hypothesis_id="h1",
            statement="Hypothesis",
            status=HypothesisStatus.PROPOSED,
        )
        inv = Investigation(
            investigation_id="inv_complex",
            title="Complex",
            objective="Test nested data",
            sources=(s,),
            evidence=(e,),
            findings=(f,),
            hypotheses=(h,),
            open_questions=("Q1?",),
        )
        repo.save(inv)
        loaded = repo.get("inv_complex")
        assert loaded is not None
        assert len(loaded.sources) == 1
        assert loaded.sources[0].source_type == SourceType.PAPER
        assert len(loaded.evidence) == 1
        assert len(loaded.findings) == 1
        assert loaded.findings[0].support == SupportState.SUPPORTED
        assert len(loaded.hypotheses) == 1
        assert loaded.hypotheses[0].status == HypothesisStatus.PROPOSED
        assert loaded.open_questions == ("Q1?",)


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestInvestigationService:
    def _make_service(self, tmp_path: Path, **kwargs) -> InvestigationService:
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        return InvestigationService(repository=repo, **kwargs)

    def test_create_investigation(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="Test", objective="Learn X", tags=("x",))
        assert inv.status == InvestigationStatus.NEW
        assert inv.title == "Test"
        assert inv.tags == ("x",)
        assert inv.investigation_id.startswith("inv_")

    def test_get_investigation(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        loaded = svc.get_investigation(inv.investigation_id)
        assert loaded is not None
        assert loaded.title == "T"

    def test_list_investigations(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        svc.create_investigation(title="A", objective="O1")
        svc.create_investigation(title="B", objective="O2")
        all_inv = svc.list_investigations()
        assert len(all_inv) == 2

    def test_delete_investigation(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        assert svc.delete_investigation(inv.investigation_id) is True
        assert svc.get_investigation(inv.investigation_id) is None


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestInvestigationLifecycle:
    def _make_service(self, tmp_path: Path) -> InvestigationService:
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        return InvestigationService(repository=repo)

    def test_status_transitions(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        assert inv.status == InvestigationStatus.NEW

        inv = svc.set_status(inv.investigation_id, "active")
        assert inv.status == InvestigationStatus.ACTIVE

        inv = svc.set_status(inv.investigation_id, InvestigationStatus.PAUSED)
        assert inv.status == InvestigationStatus.PAUSED

        inv = svc.set_status(inv.investigation_id, "completed")
        assert inv.status == InvestigationStatus.COMPLETED

    def test_conduct_research_transitions_new_to_active(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        svc._research_service = FakeResearchService()
        inv = svc.create_investigation(title="T", objective="O")
        assert inv.status == InvestigationStatus.NEW

        inv = svc.conduct_research(inv.investigation_id)
        assert inv.status == InvestigationStatus.ACTIVE

    def test_conduct_research_merges_findings(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        fake = FakeResearchService()
        svc._research_service = fake
        inv = svc.create_investigation(title="T", objective="O")

        inv = svc.conduct_research(inv.investigation_id)
        assert len(inv.findings) == 1
        assert len(inv.sources) == 1
        assert len(inv.evidence) == 1
        assert len(inv.open_questions) == 1

    def test_conduct_research_deduplicates(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        fake = FakeResearchService()
        svc._research_service = fake
        inv = svc.create_investigation(title="T", objective="O")

        inv = svc.conduct_research(inv.investigation_id)
        inv = svc.conduct_research(inv.investigation_id)

        # Second call should not duplicate
        assert len(inv.sources) == 1
        assert len(inv.findings) == 1
        assert len(inv.open_questions) == 1

    def test_conduct_research_without_service_raises(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        import pytest

        with pytest.raises(RuntimeError, match="No ResearchService"):
            svc.conduct_research(inv.investigation_id)

    def test_conduct_research_missing_inv_raises(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        svc._research_service = FakeResearchService()
        import pytest

        with pytest.raises(ValueError, match="not found"):
            svc.conduct_research("inv_nonexistent")


# ---------------------------------------------------------------------------
# Hypothesis tests
# ---------------------------------------------------------------------------


class TestInvestigationHypotheses:
    def _make_service(self, tmp_path: Path) -> InvestigationService:
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        return InvestigationService(repository=repo)

    def test_add_hypothesis(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_hypothesis(
            inv.investigation_id,
            "X causes Y",
            rationale="Based on prior studies",
        )
        assert len(inv.hypotheses) == 1
        assert inv.hypotheses[0].statement == "X causes Y"
        assert inv.hypotheses[0].status == HypothesisStatus.PROPOSED
        assert inv.hypotheses[0].rationale == "Based on prior studies"

    def test_update_hypothesis_status(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_hypothesis(inv.investigation_id, "X causes Y")
        hyp_id = inv.hypotheses[0].hypothesis_id

        inv = svc.update_hypothesis(
            inv.investigation_id,
            hyp_id,
            status=HypothesisStatus.SUPPORTED,
            evidence_ids=("ev_1", "ev_2"),
        )
        assert inv.hypotheses[0].status == HypothesisStatus.SUPPORTED
        assert inv.hypotheses[0].evidence_ids == ("ev_1", "ev_2")

    def test_update_hypothesis_missing_raises(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        import pytest

        with pytest.raises(ValueError, match="not found"):
            svc.update_hypothesis(inv.investigation_id, "hyp_ghost", status="refuted")


# ---------------------------------------------------------------------------
# Finding & question tests
# ---------------------------------------------------------------------------


class TestInvestigationFindingsAndQuestions:
    def _make_service(self, tmp_path: Path) -> InvestigationService:
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        return InvestigationService(repository=repo)

    def test_add_finding(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_finding(
            inv.investigation_id,
            "Key finding",
            evidence_ids=("ev_1",),
            support=SupportState.SUPPORTED,
        )
        assert len(inv.findings) == 1
        assert inv.findings[0].statement == "Key finding"

    def test_add_open_question(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_open_question(inv.investigation_id, "What about Z?")
        assert "What about Z?" in inv.open_questions

    def test_add_duplicate_question_is_noop(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_open_question(inv.investigation_id, "Q?")
        inv = svc.add_open_question(inv.investigation_id, "Q?")
        assert len(inv.open_questions) == 1

    def test_resolve_open_question(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_open_question(inv.investigation_id, "Q?")
        inv = svc.resolve_open_question(inv.investigation_id, "Q?")
        assert len(inv.open_questions) == 0


# ---------------------------------------------------------------------------
# Context-informed creation tests
# ---------------------------------------------------------------------------


class TestInvestigationContext:
    def _make_service(self, tmp_path: Path) -> InvestigationService:
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        return InvestigationService(repository=repo)

    def test_create_from_context(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        ctx = NavContext(
            user=UserContext(user_id="u1"),
            session=SessionContext(session_id="s1"),
            conversation=ConversationContext(conversation_id="c1"),
            personal_context=PersonalContext(
                projects=(
                    Project(
                        project_id="p1",
                        name="Battery Research",
                        current_focus="electrolytes",
                    ),
                ),
                current_focus=CurrentFocus(
                    project_id="p1",
                    topic="solid-state",
                ),
            ),
        )
        inv = svc.create_from_context(ctx, title="Electrolyte investigation")
        assert inv.project_id == "p1"
        assert "solid-state" in inv.tags
        assert "Battery Research" in inv.tags

    def test_create_from_context_no_personal(self, tmp_path: Path):
        svc = self._make_service(tmp_path)
        ctx = NavContext(
            user=UserContext(user_id="u1"),
            session=SessionContext(session_id="s1"),
            conversation=ConversationContext(conversation_id="c1"),
        )
        inv = svc.create_from_context(ctx, title="Generic research")
        assert inv.project_id is None
        assert inv.goal_id is None
