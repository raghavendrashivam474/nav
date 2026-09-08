"""
NAV v2 — S28: Decision Engine.

Executes explicit, inspectable, and traceable alternative evaluation.
Prefers deterministic evaluation of constraints, and uses AI-assisted
semantic analysis only for qualitative trade-off resolution, with strict
JSON schema validation and safe fallback.
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import uuid4

from core.contracts.ai import AIGateway, AIMessage, AIRequest
from core.contracts.decision import (
    AlternativeEvaluation,
    ConstraintType,
    DecisionAlternative,
    DecisionInput,
    DecisionResult,
    DecisionState,
)
from core.log import get_logger

logger = get_logger(__name__)


class DecisionEngine:
    """
    Engine evaluating decision alternatives against objectives and criteria.

    Implements a deterministic-first evaluation pipeline:
    1. Input validation (check for empty objectives, questions, or alternatives).
    2. Hard constraint filtering (disqualify alternatives violating HARD criteria).
    3. Auto-selection (if exactly one feasible alternative remains).
    4. Model-assisted trade-off analysis (when multiple alternatives remain, using
       semantic interpretation of supporting reasoning results).
    5. Validation & Fallback (safely rejecting invalid model outputs).
    """

    _VALID_STATES = {s.value for s in DecisionState}

    def __init__(self, gateway: AIGateway | None = None) -> None:
        self._gateway = gateway

    def decide(
        self,
        decision_input: DecisionInput,
        pre_evaluated_evaluations: list[AlternativeEvaluation] | None = None,
    ) -> DecisionResult:
        """Execute the decision pipeline over the supplied input."""
        decision_id = str(uuid4())

        # 1. Input Validation
        if (
            not decision_input.question.strip()
            or not decision_input.objective.strip()
            or not decision_input.alternatives
        ):
            return DecisionResult(
                decision_id=decision_id,
                question=decision_input.question,
                objective=decision_input.objective,
                state=DecisionState.INSUFFICIENT_INPUTS,
                alternatives=decision_input.alternatives,
                criteria=decision_input.criteria,
                rationale="Decision question, objective, and alternatives must not be empty.",
            )

        # Map pre-evaluated constraints or initialize them
        eval_map: dict[tuple[str, str], AlternativeEvaluation] = {}
        if pre_evaluated_evaluations:
            for ev in pre_evaluated_evaluations:
                eval_map[(ev.alternative_id, ev.criterion_id)] = ev

        # 2. Hard Constraint Filtering
        hard_criteria = [
            c for c in decision_input.criteria if c.constraint_type == ConstraintType.HARD
        ]
        disqualified_alts: set[str] = set()
        deterministic_evals: list[AlternativeEvaluation] = []

        # Evaluate hard constraints.
        for alt in decision_input.alternatives:
            for crit in hard_criteria:
                key = (alt.alternative_id, crit.criterion_id)
                if key in eval_map:
                    ev = eval_map[key]
                else:
                    ev = AlternativeEvaluation(
                        alternative_id=alt.alternative_id,
                        criterion_id=crit.criterion_id,
                        satisfies=True,
                        assessment="Deterministically satisfied (no violating evidence).",
                    )
                deterministic_evals.append(ev)
                if not ev.satisfies:
                    disqualified_alts.add(alt.alternative_id)

        feasible_alts = [
            alt
            for alt in decision_input.alternatives
            if alt.alternative_id not in disqualified_alts
        ]

        # 3. Handle Edge Cases Deterministically
        if not feasible_alts:
            return DecisionResult(
                decision_id=decision_id,
                question=decision_input.question,
                objective=decision_input.objective,
                state=DecisionState.NO_FEASIBLE_ALTERNATIVE,
                alternatives=decision_input.alternatives,
                criteria=decision_input.criteria,
                evaluations=tuple(deterministic_evals),
                rationale="All consideration options violated at least one hard constraint.",
                reasoning_basis=decision_input.reasoning_basis,
                comparison_basis=decision_input.comparison_basis,
                finding_basis=decision_input.finding_basis,
                evidence_basis=decision_input.evidence_basis,
            )

        if len(feasible_alts) == 1:
            selected = feasible_alts[0]
            return DecisionResult(
                decision_id=decision_id,
                question=decision_input.question,
                objective=decision_input.objective,
                state=DecisionState.DECIDED,
                alternatives=decision_input.alternatives,
                criteria=decision_input.criteria,
                evaluations=tuple(deterministic_evals),
                selected_alternative_id=selected.alternative_id,
                rationale=(
                    f"Selected '{selected.label}' deterministically because it is the "
                    "only alternative that satisfied all hard constraints."
                ),
                reasoning_basis=decision_input.reasoning_basis,
                comparison_basis=decision_input.comparison_basis,
                finding_basis=decision_input.finding_basis,
                evidence_basis=decision_input.evidence_basis,
            )

        # 4. Model-Assisted qualitative synthesis (or fallback if gateway missing)
        if not self._gateway:
            return self._fallback_undecided(
                decision_id,
                decision_input,
                deterministic_evals,
                "Multiple options are feasible but no AI Gateway is available.",
            )

        return self._decide_semantic(
            decision_id, decision_input, feasible_alts, deterministic_evals
        )

    def _decide_semantic(
        self,
        decision_id: str,
        decision_input: DecisionInput,
        feasible_alts: list[DecisionAlternative],
        deterministic_evals: list[AlternativeEvaluation],
    ) -> DecisionResult:
        """Utilize the AI gateway for qualitative evaluation over surviving alternatives."""
        alts_lines = [
            f"- ID: {a.alternative_id} | Label: {a.label} | Description: {a.description}"
            for a in feasible_alts
        ]
        alts_str = "\n".join(alts_lines)

        soft_criteria = [
            c for c in decision_input.criteria if c.constraint_type == ConstraintType.SOFT
        ]
        crit_lines = [
            f"- ID: {c.criterion_id} | Name: {c.name} | Description: {c.description}"
            for c in soft_criteria
        ]
        criteria_str = "\n".join(crit_lines)

        system_prompt = (
            "You are NAV's explicit decision module (S28).\n"
            "Evaluate feasible alternatives against the objective and preferences.\n"
            "Return a valid JSON object matching the requested schema:\n"
            "selected_alternative_id, state (decided/contested/inconclusive),\n"
            "rationale, trade_offs, risks, limitations, and evaluations.\n"
            "Rules:\n"
            "1. Select ONLY from provided feasible alternative IDs. Never invent IDs.\n"
            "2. Never bypass hard constraints.\n"
            "3. If equally good, set state to 'contested' or 'inconclusive'.\n"
            "4. Rationale must link to provided basis."
        )

        user_content = (
            f"Decision Question: {decision_input.question}\n"
            f"Objective: {decision_input.objective}\n\n"
            f"Feasible Alternatives:\n{alts_str}\n\n"
            f"Preferences / Soft Criteria:\n{criteria_str or 'None'}\n\n"
            "Please analyze and select the optimal alternative according to the objective."
        )

        try:
            req = AIRequest(
                messages=[
                    AIMessage(role="system", content=system_prompt),
                    AIMessage(role="user", content=user_content),
                ],
                temperature=0.1,
            )
            response = self._gateway.generate(req)
            parsed = self._clean_and_parse_json(response.content)

            raw_state = parsed.get("state", "inconclusive").lower()
            state = DecisionState.INCONCLUSIVE
            if raw_state == "decided":
                state = DecisionState.DECIDED
            elif raw_state == "contested":
                state = DecisionState.CONTESTED

            selected_id = parsed.get("selected_alternative_id")
            feasible_ids = {a.alternative_id for a in feasible_alts}

            if state == DecisionState.DECIDED:
                if not selected_id or selected_id not in feasible_ids:
                    logger.warning(
                        "Model selected invalid/non-feasible ID: %s. Falling back to CONTESTED.",
                        selected_id,
                    )
                    return self._fallback_undecided(
                        decision_id,
                        decision_input,
                        deterministic_evals,
                        f"Model generated invalid alternative ID selection: {selected_id}",
                    )

            model_evals = parsed.get("evaluations", [])
            all_evals = list(deterministic_evals)

            valid_criterion_ids = {c.criterion_id for c in decision_input.criteria}
            for ev in model_evals:
                alt_id = ev.get("alternative_id")
                crit_id = ev.get("criterion_id")
                if alt_id in feasible_ids and crit_id in valid_criterion_ids:
                    all_evals.append(
                        AlternativeEvaluation(
                            alternative_id=alt_id,
                            criterion_id=crit_id,
                            satisfies=bool(ev.get("satisfies", True)),
                            assessment=str(ev.get("assessment", "Evaluated qualitatively.")),
                        )
                    )

            return DecisionResult(
                decision_id=decision_id,
                question=decision_input.question,
                objective=decision_input.objective,
                state=state,
                alternatives=decision_input.alternatives,
                criteria=decision_input.criteria,
                evaluations=tuple(all_evals),
                selected_alternative_id=selected_id if state == DecisionState.DECIDED else None,
                rationale=str(parsed.get("rationale", "Qualitative evaluation performed.")),
                trade_offs=str(parsed.get("trade_offs", "")),
                risks=str(parsed.get("risks", "")),
                limitations=str(parsed.get("limitations", "")),
                reasoning_basis=decision_input.reasoning_basis,
                comparison_basis=decision_input.comparison_basis,
                finding_basis=decision_input.finding_basis,
                evidence_basis=decision_input.evidence_basis,
            )

        except Exception as exc:
            logger.error("DecisionEngine semantic routing error: %s", exc)
            return self._fallback_undecided(
                decision_id,
                decision_input,
                deterministic_evals,
                f"Model evaluation failed or timed out. Fallback triggered. Error: {exc!s}",
            )

    def _fallback_undecided(
        self,
        decision_id: str,
        decision_input: DecisionInput,
        evals: list[AlternativeEvaluation],
        fallback_reason: str,
    ) -> DecisionResult:
        """Produces a safe, undecided DecisionResult when semantic evaluation is unavailable."""
        return DecisionResult(
            decision_id=decision_id,
            question=decision_input.question,
            objective=decision_input.objective,
            state=DecisionState.CONTESTED,
            alternatives=decision_input.alternatives,
            criteria=decision_input.criteria,
            evaluations=tuple(evals),
            rationale=f"Decision remains unresolved. Basis: {fallback_reason}",
            reasoning_basis=decision_input.reasoning_basis,
            comparison_basis=decision_input.comparison_basis,
            finding_basis=decision_input.finding_basis,
            evidence_basis=decision_input.evidence_basis,
        )

    def _clean_and_parse_json(self, raw: str) -> dict[str, Any]:
        """Cleans Markdown wrapping and parses JSON output safely."""
        content = raw.strip()
        if content.startswith("```"):
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
            if match:
                content = match.group(1).strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse JSON directly: %s", exc)
            raise ValueError(f"Invalid JSON response from decision model: {exc!s}")
