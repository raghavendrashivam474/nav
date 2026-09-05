"""Comprehensive test suite for S16 — Investigation Continuity."""

from __future__ import annotations

from pathlib import Path

from capabilities.research.investigation.continuity.service import (
    InvestigationContinuityService,
)
from capabilities.research.investigation.models import (
    ActivityType,
    HypothesisStatus,
    Investigation,
    InvestigationStatus,
)
from capabilities.research.investigation.service import InvestigationService
from capabilities.research.investigation.sqlite_repo import (
    SQLiteInvestigationRepository,
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
# Fake ResearchService (same pattern as S15 tests)
# ---------------------------------------------------------------------------


class FakeResearchService:
    def __init__(self) -> None:
        self.calls: list[ResearchQuery] = []

    def execute_research(self, query: ResearchQuery) -> ResearchResult:
        self.calls.append(query)
        s1 = ResearchSource(
            source_id="src_s16_1",
            url="https://example.com/s16",
            canonical_url="https://example.com/s16",
            title="S16 Source",
            source_type=SourceType.ARTICLE,
            status=SourceStatus.RETRIEVED,
        )
        e1 = ResearchEvidence(
            evidence_id="ev_s16_1",
            source_id="src_s16_1",
            claim="S16 claim",
            excerpt="excerpt",
            relevance="high",
        )
        f1 = ResearchFinding(
            statement="S16 finding about the topic.",
            evidence_ids=("ev_s16_1",),
            support=SupportState.SUPPORTED,
        )
        return ResearchResult(
            query=query,
            sources=(s1,),
            evidence=(e1,),
            findings=(f1,),
            open_questions=("What about S16 edge cases?",),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(tmp_path: Path, **kwargs) -> InvestigationService:
    repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
    return InvestigationService(repository=repo, **kwargs)


def _make_continuity(tmp_path: Path) -> InvestigationContinuityService:
    repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
    repo.initialize()
    return InvestigationContinuityService(repository=repo)


# ---------------------------------------------------------------------------
# Activity logging tests
# ---------------------------------------------------------------------------


class TestActivityLogging:
    def test_conduct_research_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc._research_service = FakeResearchService()
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.conduct_research(inv.investigation_id)

        assert len(inv.activity_log) >= 1
        last = inv.activity_log[-1]
        assert last.activity_type == ActivityType.RESEARCH_CONDUCTED
        assert "Researched" in last.description

    def test_add_hypothesis_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_hypothesis(inv.investigation_id, "X causes Y")

        assert any(
            a.activity_type == ActivityType.HYPOTHESIS_ADDED
            for a in inv.activity_log
        )

    def test_update_hypothesis_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_hypothesis(inv.investigation_id, "X causes Y")
        hyp_id = inv.hypotheses[0].hypothesis_id
        inv = svc.update_hypothesis(
            inv.investigation_id, hyp_id, status=HypothesisStatus.SUPPORTED
        )

        assert any(
            a.activity_type == ActivityType.HYPOTHESIS_UPDATED
            for a in inv.activity_log
        )

    def test_add_finding_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_finding(inv.investigation_id, "Key finding")

        assert any(
            a.activity_type == ActivityType.FINDING_ADDED
            for a in inv.activity_log
        )

    def test_add_open_question_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_open_question(inv.investigation_id, "What about Z?")

        assert any(
            a.activity_type == ActivityType.QUESTION_ADDED
            for a in inv.activity_log
        )

    def test_resolve_question_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_open_question(inv.investigation_id, "Q?")
        inv = svc.resolve_open_question(inv.investigation_id, "Q?")

        assert any(
            a.activity_type == ActivityType.QUESTION_RESOLVED
            for a in inv.activity_log
        )

    def test_set_status_records_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.set_status(inv.investigation_id, "active")

        assert any(
            a.activity_type == ActivityType.STATUS_CHANGED
            for a in inv.activity_log
        )

    def test_activity_log_survives_persistence(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_finding(inv.investigation_id, "Persistent finding")
        inv_id = inv.investigation_id

        loaded = svc.get_investigation(inv_id)
        assert loaded is not None
        assert len(loaded.activity_log) >= 1
        assert loaded.activity_log[-1].activity_type == ActivityType.FINDING_ADDED


# ---------------------------------------------------------------------------
# Resolution tests
# ---------------------------------------------------------------------------


class TestInvestigationResolution:
    def test_exact_id_match(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="Local AI", objective="Viability")
        cs = InvestigationContinuityService(repository=svc._repo)

        result = cs.resolve_investigation(inv.investigation_id)
        assert result.confidence == "high"
        assert result.resolved_id == inv.investigation_id

    def test_title_substring_match(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc.create_investigation(title="Local AI for NAV", objective="Test")
        cs = InvestigationContinuityService(repository=svc._repo)

        result = cs.resolve_investigation("local AI")
        assert result.confidence in ("high", "medium")
        assert result.resolved_id is not None

    def test_no_match(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc.create_investigation(title="Batteries", objective="Solid-state")
        cs = InvestigationContinuityService(repository=svc._repo)

        result = cs.resolve_investigation("quantum computing")
        assert result.confidence == "none"
        assert result.resolved_id is None

    def test_ambiguous_matches(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc.create_investigation(title="Local AI for NAV", objective="Test")
        svc.create_investigation(title="Local AI for assistants", objective="Test")
        cs = InvestigationContinuityService(repository=svc._repo)

        result = cs.resolve_investigation("Local AI")
        # Both should match with similar scores
        assert len(result.matches) >= 2
        assert result.confidence == "low"
        assert result.resolved_id is None

    def test_project_match_fallback(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc.create_investigation(
            title="Something",
            objective="Something else",
            project_id="proj_x",
        )
        cs = InvestigationContinuityService(repository=svc._repo)

        result = cs.resolve_investigation(
            "unrelated query", project_id="proj_x"
        )
        assert len(result.matches) >= 1

    def test_empty_database(self, tmp_path: Path):
        cs = _make_continuity(tmp_path)
        result = cs.resolve_investigation("anything")
        assert result.confidence == "none"


# ---------------------------------------------------------------------------
# Continuation snapshot tests
# ---------------------------------------------------------------------------


class TestContinuationSnapshot:
    def test_basic_continuation(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="Learn X")
        inv = svc.add_finding(
            inv.investigation_id, "X is viable", support=SupportState.SUPPORTED
        )
        inv = svc.add_open_question(inv.investigation_id, "What about cost?")
        cs = InvestigationContinuityService(repository=svc._repo)

        cont = cs.build_continuation(inv)
        assert cont.investigation_id == inv.investigation_id
        assert cont.title == "T"
        assert "X is viable" in cont.established_findings
        assert "What about cost?" in cont.open_questions
        assert cont.source_count == 0
        assert len(cont.suggested_directions) >= 1

    def test_continuation_with_hypotheses(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_hypothesis(inv.investigation_id, "H1")
        cs = InvestigationContinuityService(repository=svc._repo)

        cont = cs.build_continuation(inv)
        assert len(cont.active_hypotheses) == 1
        assert "proposed" in cont.active_hypotheses[0]

    def test_continuation_with_conflicts(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        cs = InvestigationContinuityService(repository=svc._repo)

        # Manually add a conflict via the model
        from dataclasses import replace

        conflict = ResearchFinding(
            statement="Sources disagree on X",
            evidence_ids=(),
            support=SupportState.CONFLICTING,
        )
        inv = replace(inv, conflicts=(conflict,))
        svc._repo.update(inv)

        cont = cs.build_continuation(inv)
        assert "Sources disagree on X" in cont.contradictions

    def test_continuation_recent_activity(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        inv = svc.add_finding(inv.investigation_id, "F1")
        cs = InvestigationContinuityService(repository=svc._repo)

        cont = cs.build_continuation(inv)
        assert "finding_added" in cont.recent_activity

    def test_continuation_no_activity(self, tmp_path: Path):
        inv = Investigation(
            investigation_id="inv_empty",
            title="T",
            objective="O",
        )
        cs = _make_continuity(tmp_path)
        cont = cs.build_continuation(inv)
        assert cont.recent_activity == "No recorded activity."

    def test_continuation_does_not_mutate_investigation(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O")
        cs = InvestigationContinuityService(repository=svc._repo)

        original_id = inv.investigation_id
        _ = cs.build_continuation(inv)

        loaded = svc.get_investigation(original_id)
        assert loaded is not None
        assert loaded.title == "T"
        assert len(loaded.findings) == 0


# ---------------------------------------------------------------------------
# Resume (combined) tests
# ---------------------------------------------------------------------------


class TestResume:
    def test_resume_success(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="Local AI", objective="Viability")
        inv = svc.add_finding(
            inv.investigation_id, "GPU needed", support=SupportState.SUPPORTED
        )
        cs = InvestigationContinuityService(repository=svc._repo)

        resolution, cont = cs.resume("Local AI")
        assert resolution.confidence in ("high", "medium")
        assert cont is not None
        assert cont.title == "Local AI"
        assert "GPU needed" in cont.established_findings

    def test_resume_no_match(self, tmp_path: Path):
        cs = _make_continuity(tmp_path)
        resolution, cont = cs.resume("nonexistent topic")
        assert resolution.confidence == "none"
        assert cont is None

    def test_resume_ambiguous(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc.create_investigation(title="Local AI NAV", objective="O")
        svc.create_investigation(title="Local AI personal", objective="O")
        cs = InvestigationContinuityService(repository=svc._repo)

        resolution, cont = cs.resume("Local AI")
        assert resolution.confidence == "low"
        assert cont is None


# ---------------------------------------------------------------------------
# Continue after resume tests
# ---------------------------------------------------------------------------


class TestContinueAfterResume:
    def test_research_updates_same_investigation(self, tmp_path: Path):
        svc = _make_service(tmp_path)
        svc._research_service = FakeResearchService()
        inv = svc.create_investigation(title="T", objective="O")
        inv_id = inv.investigation_id

        # Simulate resume + continue
        inv = svc.conduct_research(inv_id)
        assert len(inv.findings) >= 1

        # Second research round
        inv = svc.conduct_research(inv_id, query_override="deeper question")
        loaded = svc.get_investigation(inv_id)
        assert loaded is not None
        assert loaded.investigation_id == inv_id
        assert len(loaded.activity_log) >= 2


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_old_investigation_without_activity_log(self, tmp_path: Path):
        """Simulate an S15-era investigation with no activity_log."""
        repo = SQLiteInvestigationRepository(db_path=tmp_path / "inv.db")
        repo.initialize()

        inv = Investigation(
            investigation_id="inv_legacy",
            title="Legacy",
            objective="Old investigation",
        )
        repo.save(inv)

        loaded = repo.get("inv_legacy")
        assert loaded is not None
        assert loaded.activity_log == ()

        cs = InvestigationContinuityService(repository=repo)
        cont = cs.build_continuation(loaded)
        assert cont.recent_activity == "No recorded activity."

    def test_s15_tests_still_pass(self, tmp_path: Path):
        """Verify core S15 operations still work unchanged."""
        svc = _make_service(tmp_path)
        inv = svc.create_investigation(title="T", objective="O", tags=("x",))
        assert inv.status == InvestigationStatus.NEW
        assert inv.tags == ("x",)

        loaded = svc.get_investigation(inv.investigation_id)
        assert loaded is not None
        assert loaded.title == "T"

        all_inv = svc.list_investigations()
        assert len(all_inv) == 1

        assert svc.delete_investigation(inv.investigation_id) is True
        assert svc.get_investigation(inv.investigation_id) is None
