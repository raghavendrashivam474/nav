"""
NAV v2 — S28: Decision Tests.

Covers contracts, deterministic evaluation, constraint filtering,
model-assisted reasoning integration, service facade, and capability routing.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from capabilities.decision.capability import DecisionCapability
from capabilities.decision.engine import DecisionEngine
from capabilities.decision.service import DecisionService
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.capability import Request
from core.contracts.decision import (
    AlternativeEvaluation,
    ConstraintType,
    DecisionAlternative,
    DecisionCriterion,
    DecisionInput,
    DecisionResult,
    DecisionState,
)

# ---------------------------------------------------------------------------
# Test Doubles
# ---------------------------------------------------------------------------


class _StaticGateway(AIGateway):
    def __init__(self, response_content: str) -> None:
        self._content = response_content
        self.last_request: AIRequest | None = None

    def generate(self, request: AIRequest) -> AIResponse:
        self.last_request = request
        return AIResponse(
            content=self._content,
            model_used="test-mock",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )


class _FailingGateway(AIGateway):
    def generate(self, request: AIRequest) -> AIResponse:
        raise RuntimeError("simulated gateway failure")


# ---------------------------------------------------------------------------
# 1. Contract Tests
# ---------------------------------------------------------------------------


class TestDecisionContracts:
    def test_alternative_valid(self) -> None:
        alt = DecisionAlternative(alternative_id="a1", label="Option A")
        assert alt.alternative_id == "a1"
        assert alt.label == "Option A"
        assert alt.description == ""

    def test_alternative_rejects_empty_id(self) -> None:
        with pytest.raises(ValueError, match="alternative_id must not be empty"):
            DecisionAlternative(alternative_id="", label="Option A")

    def test_alternative_rejects_empty_label(self) -> None:
        with pytest.raises(ValueError, match="label must not be empty"):
            DecisionAlternative(alternative_id="a1", label="")

    def test_alternative_immutable(self) -> None:
        alt = DecisionAlternative(alternative_id="a1", label="Option A")
        with pytest.raises(FrozenInstanceError):
            alt.label = "Changed"  # type: ignore[misc]

    def test_criterion_valid(self) -> None:
        crit = DecisionCriterion(
            criterion_id="c1",
            name="Budget",
            constraint_type=ConstraintType.HARD,
            threshold="<= 100k",
        )
        assert crit.criterion_id == "c1"
        assert crit.constraint_type == ConstraintType.HARD

    def test_criterion_rejects_empty_fields(self) -> None:
        with pytest.raises(ValueError, match="criterion_id"):
            DecisionCriterion(criterion_id="", name="Budget")
        with pytest.raises(ValueError, match="name"):
            DecisionCriterion(criterion_id="c1", name="")

    def test_evaluation_valid(self) -> None:
        ev = AlternativeEvaluation(
            alternative_id="a1",
            criterion_id="c1",
            satisfies=True,
            assessment="Fits budget",
        )
        assert ev.satisfies is True
        assert ev.assessment == "Fits budget"

    def test_evaluation_rejects_empty_assessment(self) -> None:
        with pytest.raises(ValueError, match="assessment"):
            AlternativeEvaluation(
                alternative_id="a1",
                criterion_id="c1",
                satisfies=True,
                assessment="",
            )

    def test_input_valid(self) -> None:
        inp = DecisionInput(
            question="Which database?",
            objective="Maximize throughput",
            alternatives=(
                DecisionAlternative("pg", "Postgres"),
                DecisionAlternative("my", "MySQL"),
            ),
        )
        assert inp.question == "Which database?"
        assert len(inp.alternatives) == 2

    def test_input_rejects_empty_question(self) -> None:
        with pytest.raises(ValueError, match="question"):
            DecisionInput(
                question="",
                objective="Maximize throughput",
                alternatives=(DecisionAlternative("pg", "Postgres"),),
            )

    def test_input_rejects_empty_objective(self) -> None:
        with pytest.raises(ValueError, match="objective"):
            DecisionInput(
                question="Which DB?",
                objective="",
                alternatives=(DecisionAlternative("pg", "Postgres"),),
            )

    def test_input_rejects_no_alternatives(self) -> None:
        with pytest.raises(ValueError, match="at least one alternative"):
            DecisionInput(
                question="Which DB?",
                objective="Fast",
                alternatives=(),
            )

    def test_result_decided_requires_selected_id(self) -> None:
        with pytest.raises(ValueError, match="must have a selected_alternative_id"):
            DecisionResult(
                decision_id="d1",
                question="Which DB?",
                objective="Fast",
                state=DecisionState.DECIDED,
                alternatives=(DecisionAlternative("pg", "Postgres"),),
                selected_alternative_id=None,
            )

    def test_result_selected_must_exist_in_alternatives(self) -> None:
        with pytest.raises(ValueError, match="not found in alternatives"):
            DecisionResult(
                decision_id="d1",
                question="Which DB?",
                objective="Fast",
                state=DecisionState.DECIDED,
                alternatives=(DecisionAlternative("pg", "Postgres"),),
                selected_alternative_id="nonexistent",
            )

    def test_result_no_feasible_cannot_have_selection(self) -> None:
        with pytest.raises(ValueError, match="must not have a selected_alternative_id"):
            DecisionResult(
                decision_id="d1",
                question="Which DB?",
                objective="Fast",
                state=DecisionState.NO_FEASIBLE_ALTERNATIVE,
                alternatives=(DecisionAlternative("pg", "Postgres"),),
                selected_alternative_id="pg",
            )

    def test_result_insufficient_cannot_have_selection(self) -> None:
        with pytest.raises(ValueError, match="must not have a selected_alternative_id"):
            DecisionResult(
                decision_id="d1",
                question="Which DB?",
                objective="Fast",
                state=DecisionState.INSUFFICIENT_INPUTS,
                alternatives=(DecisionAlternative("pg", "Postgres"),),
                selected_alternative_id="pg",
            )


# ---------------------------------------------------------------------------
# 2. Engine Deterministic Tests
# ---------------------------------------------------------------------------


class TestDecisionEngineDeterministic:
    def setup_method(self) -> None:
        self.engine = DecisionEngine(gateway=None)

    def test_single_survivor_selected(self) -> None:
        inp = DecisionInput(
            question="Which car?",
            objective="Budget friendly",
            alternatives=(
                DecisionAlternative("a", "Car A"),
                DecisionAlternative("b", "Car B"),
            ),
            criteria=(
                DecisionCriterion("c1", "Budget", constraint_type=ConstraintType.HARD),
            ),
        )
        evals = [
            AlternativeEvaluation("a", "c1", True, "Within budget"),
            AlternativeEvaluation("b", "c1", False, "Exceeds budget"),
        ]
        result = self.engine.decide(inp, evals)
        assert result.state == DecisionState.DECIDED
        assert result.selected_alternative_id == "a"
        assert "only alternative that satisfied all hard constraints" in result.rationale

    def test_all_disqualified_yields_no_feasible(self) -> None:
        inp = DecisionInput(
            question="Which car?",
            objective="Budget friendly",
            alternatives=(
                DecisionAlternative("a", "Car A"),
                DecisionAlternative("b", "Car B"),
            ),
            criteria=(
                DecisionCriterion("c1", "Budget", constraint_type=ConstraintType.HARD),
            ),
        )
        evals = [
            AlternativeEvaluation("a", "c1", False, "Exceeds budget"),
            AlternativeEvaluation("b", "c1", False, "Exceeds budget"),
        ]
        result = self.engine.decide(inp, evals)
        assert result.state == DecisionState.NO_FEASIBLE_ALTERNATIVE
        assert result.selected_alternative_id is None

    def test_multiple_survivors_without_gateway_yields_contested(self) -> None:
        inp = DecisionInput(
            question="Which car?",
            objective="Budget friendly",
            alternatives=(
                DecisionAlternative("a", "Car A"),
                DecisionAlternative("b", "Car B"),
            ),
            criteria=(
                DecisionCriterion("c1", "Budget", constraint_type=ConstraintType.HARD),
            ),
        )
        evals = [
            AlternativeEvaluation("a", "c1", True, "Within budget"),
            AlternativeEvaluation("b", "c1", True, "Within budget"),
        ]
        result = self.engine.decide(inp, evals)
        assert result.state == DecisionState.CONTESTED
        assert result.selected_alternative_id is None
        assert "no AI Gateway is available" in result.rationale

    def test_preserves_provenance_basis(self) -> None:
        inp = DecisionInput(
            question="Which option?",
            objective="Test",
            alternatives=(DecisionAlternative("a", "Option A"),),
            reasoning_basis=("r1", "r2"),
            comparison_basis=("cmp1",),
            finding_basis=("f1", "f2"),
            evidence_basis=("e1",),
        )
        result = self.engine.decide(inp)
        assert result.reasoning_basis == ("r1", "r2")
        assert result.comparison_basis == ("cmp1",)
        assert result.finding_basis == ("f1", "f2")
        assert result.evidence_basis == ("e1",)


# ---------------------------------------------------------------------------
# 3. Engine Model-Assisted Tests
# ---------------------------------------------------------------------------


class TestDecisionEngineModelAssisted:
    def test_model_selects_winner(self) -> None:
        mock_response = json.dumps({
            "selected_alternative_id": "b",
            "state": "decided",
            "rationale": "Option B offers superior performance per dollar.",
            "trade_offs": "Option B is slightly heavier.",
            "risks": "Newer vendor with shorter track record.",
            "limitations": "Benchmark data is synthetic.",
            "evaluations": [
                {
                    "alternative_id": "b",
                    "criterion_id": "c1",
                    "satisfies": True,
                    "assessment": "High perf",
                },
                {
                    "alternative_id": "a",
                    "criterion_id": "c1",
                    "satisfies": False,
                    "assessment": "Lower perf",
                },
            ],
        })
        gateway = _StaticGateway(mock_response)
        engine = DecisionEngine(gateway=gateway)

        inp = DecisionInput(
            question="Which server?",
            objective="Maximize compute",
            alternatives=(
                DecisionAlternative("a", "Server A"),
                DecisionAlternative("b", "Server B"),
            ),
            criteria=(
                DecisionCriterion(
                    criterion_id="c1",
                    name="Performance",
                    constraint_type=ConstraintType.SOFT,
                ),
            ),
        )
        result = engine.decide(inp)
        assert result.state == DecisionState.DECIDED
        assert result.selected_alternative_id == "b"
        assert result.trade_offs == "Option B is slightly heavier."
        assert result.risks == "Newer vendor with shorter track record."
        assert len(result.evaluations) == 2

    def test_model_failing_gateway_falls_back_safely(self) -> None:
        gateway = _FailingGateway()
        engine = DecisionEngine(gateway=gateway)

        inp = DecisionInput(
            question="Which server?",
            objective="Maximize compute",
            alternatives=(
                DecisionAlternative("a", "Server A"),
                DecisionAlternative("b", "Server B"),
            ),
        )
        result = engine.decide(inp)
        assert result.state == DecisionState.CONTESTED
        assert result.selected_alternative_id is None
        assert "Fallback triggered" in result.rationale

    def test_model_malformed_json_falls_back(self) -> None:
        gateway = _StaticGateway("not valid json at all")
        engine = DecisionEngine(gateway=gateway)

        inp = DecisionInput(
            question="Which server?",
            objective="Maximize compute",
            alternatives=(
                DecisionAlternative("a", "Server A"),
                DecisionAlternative("b", "Server B"),
            ),
        )
        result = engine.decide(inp)
        assert result.state == DecisionState.CONTESTED
        assert result.selected_alternative_id is None

    def test_model_markdown_wrapped_json_parsed_correctly(self) -> None:
        payload = json.dumps({
            "selected_alternative_id": "a",
            "state": "decided",
            "rationale": "Clear winner.",
            "trade_offs": "None",
            "risks": "None",
            "limitations": "None",
            "evaluations": [],
        })
        wrapped = f"```json\n{payload}\n```"
        gateway = _StaticGateway(wrapped)
        engine = DecisionEngine(gateway=gateway)

        inp = DecisionInput(
            question="Which option?",
            objective="Best",
            alternatives=(
                DecisionAlternative("a", "Option A"),
                DecisionAlternative("b", "Option B"),
            ),
        )
        result = engine.decide(inp)
        assert result.state == DecisionState.DECIDED
        assert result.selected_alternative_id == "a"


# ---------------------------------------------------------------------------
# 4. Service Tests
# ---------------------------------------------------------------------------


class TestDecisionService:
    def test_decide_delegates_to_engine(self) -> None:
        service = DecisionService()
        inp = DecisionInput(
            question="Which phone?",
            objective="Best camera",
            alternatives=(
                DecisionAlternative("p1", "Phone 1"),
                DecisionAlternative("p2", "Phone 2"),
            ),
            criteria=(
                DecisionCriterion("c1", "Price", constraint_type=ConstraintType.HARD),
            ),
        )
        evals = [
            AlternativeEvaluation("p1", "c1", True, "Under budget"),
            AlternativeEvaluation("p2", "c1", False, "Over budget"),
        ]
        result = service.decide(inp, evals)
        assert result.state == DecisionState.DECIDED
        assert result.selected_alternative_id == "p1"

    def test_service_exposes_subordinate_services(self) -> None:
        service = DecisionService()
        assert service.reasoning_service is not None
        assert service.comparison_service is not None
        assert service.evidence_service is not None


# ---------------------------------------------------------------------------
# 5. Capability Tests
# ---------------------------------------------------------------------------


class TestDecisionCapability:
    def setup_method(self) -> None:
        self.capability = DecisionCapability()

    def test_capability_metadata(self) -> None:
        assert self.capability.name == "decision"
        assert self.capability.version == "1.0.0"

    def test_invoke_valid_request(self) -> None:
        req = Request(
            request_id="req-1",
            payload={
                "action": "decide",
                "question": "Which framework?",
                "objective": "High speed",
                "alternatives": [
                    {"alternative_id": "f1", "label": "FastAPI"},
                    {"alternative_id": "f2", "label": "Flask"},
                ],
                "criteria": [
                    {"criterion_id": "c1", "name": "Async", "constraint_type": "hard"},
                ],
                "evaluations": [
                    {
                        "alternative_id": "f1",
                        "criterion_id": "c1",
                        "satisfies": True,
                        "assessment": "Native async",
                    },
                    {
                        "alternative_id": "f2",
                        "criterion_id": "c1",
                        "satisfies": False,
                        "assessment": "No native async",
                    },
                ],
            },
        )
        resp = self.capability.invoke(req)
        assert resp.success is True
        decision: DecisionResult = resp.data["decision"]
        assert decision.state == DecisionState.DECIDED
        assert decision.selected_alternative_id == "f1"

    def test_invoke_missing_question_fails(self) -> None:
        req = Request(
            request_id="req-2",
            payload={
                "action": "decide",
                "question": "",
                "objective": "Fast",
                "alternatives": [{"alternative_id": "a1", "label": "A"}],
            },
        )
        resp = self.capability.invoke(req)
        assert resp.success is False
        assert "question" in resp.error

    def test_invoke_missing_objective_fails(self) -> None:
        req = Request(
            request_id="req-3",
            payload={
                "action": "decide",
                "question": "Which?",
                "objective": "",
                "alternatives": [{"alternative_id": "a1", "label": "A"}],
            },
        )
        resp = self.capability.invoke(req)
        assert resp.success is False
        assert "objective" in resp.error

    def test_invoke_unknown_action_fails(self) -> None:
        req = Request(
            request_id="req-4",
            payload={"action": "execute_purchase"},
        )
        resp = self.capability.invoke(req)
        assert resp.success is False
        assert "Unknown decision action" in resp.error
