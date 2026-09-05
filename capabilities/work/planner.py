"""Planning subsystem — S17.

Provides deterministic and AI-assisted plan generation.

DeterministicPlanner: keyword-based template selection, no AI dependency.
AIPlanner: uses AIGateway to propose structured plans, validates strictly,
falls back to a minimal single-step plan on any failure.

Both produce immutable WorkPlan instances. AI never silently mutates state.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from core.contracts.ai import AIGateway, AIMessage, AIRequest
from core.contracts.work import WorkPlan, WorkStep
from core.log import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Deterministic Planner
# ---------------------------------------------------------------------------


class DeterministicPlanner:
    """Rule-based planner using keyword matching and templates."""

    def create_plan(
        self,
        objective: str,
        context_hints: dict | None = None,
    ) -> WorkPlan:
        now = datetime.now(timezone.utc).isoformat()
        obj_lower = objective.lower()

        if any(kw in obj_lower for kw in ("compare", "versus", "vs", "alternative")):
            steps = self._comparison_template(objective)
        elif any(kw in obj_lower for kw in ("research", "investigate", "find out", "look up")):
            steps = self._research_template(objective)
        elif any(kw in obj_lower for kw in ("analyse", "analyze", "evaluate", "assess")):
            steps = self._analysis_template(objective)
        else:
            steps = self._generic_template(objective)

        return WorkPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            steps=tuple(steps),
            version=1,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def _research_template(objective: str) -> list[WorkStep]:
        return [
            WorkStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                name="Gather information",
                description=f"Research: {objective}",
                capability="research",
                input_payload={"question": objective, "max_sources": 5},
            ),
            WorkStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                name="Synthesise findings",
                description="Review and synthesise research results",
                capability="cognition",
                input_payload={"task": "synthesise", "objective": objective},
                dependencies=(),
            ),
        ]

    @staticmethod
    def _comparison_template(objective: str) -> list[WorkStep]:
        s1_id = f"step_{uuid.uuid4().hex[:8]}"
        s2_id = f"step_{uuid.uuid4().hex[:8]}"
        return [
            WorkStep(
                step_id=s1_id,
                name="Research option A",
                description=f"Research first option for: {objective}",
                capability="research",
                input_payload={"question": objective, "max_sources": 4},
            ),
            WorkStep(
                step_id=s2_id,
                name="Research option B",
                description=f"Research second option for: {objective}",
                capability="research",
                input_payload={"question": objective, "max_sources": 4},
            ),
            WorkStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                name="Compare options",
                description="Compare gathered evidence",
                capability="cognition",
                input_payload={"task": "compare", "objective": objective},
                dependencies=(s1_id, s2_id),
            ),
        ]

    @staticmethod
    def _analysis_template(objective: str) -> list[WorkStep]:
        s1_id = f"step_{uuid.uuid4().hex[:8]}"
        return [
            WorkStep(
                step_id=s1_id,
                name="Gather data",
                description=f"Collect data for analysis: {objective}",
                capability="research",
                input_payload={"question": objective, "max_sources": 6},
            ),
            WorkStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                name="Analyse",
                description="Analyse collected data",
                capability="cognition",
                input_payload={"task": "analyse", "objective": objective},
                dependencies=(s1_id,),
            ),
        ]

    @staticmethod
    def _generic_template(objective: str) -> list[WorkStep]:
        return [
            WorkStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                name="Execute objective",
                description=f"Work toward: {objective}",
                capability="cognition",
                input_payload={"task": "execute", "objective": objective},
            ),
        ]


# ---------------------------------------------------------------------------
# AI-Assisted Planner
# ---------------------------------------------------------------------------


class AIPlanner:
    """AI-assisted planner using AIGateway with strict validation.

    Produces structured WorkPlan proposals. Falls back to a single-step
    plan if the AI output is malformed or unavailable.
    """

    def __init__(
        self, gateway: AIGateway, fallback: DeterministicPlanner | None = None
    ) -> None:
        self._gateway = gateway
        self._fallback = fallback or DeterministicPlanner()

    def create_plan(
        self,
        objective: str,
        context_hints: dict | None = None,
    ) -> WorkPlan:
        try:
            return self._ai_plan(objective, context_hints)
        except Exception as e:
            logger.warning("AI planning failed (%s), falling back to deterministic", e)
            return self._fallback.create_plan(objective, context_hints)

    def _ai_plan(self, objective: str, context_hints: dict | None) -> WorkPlan:
        hints_str = json.dumps(context_hints) if context_hints else "{}"
        prompt = (
            "You are a planning assistant. Given the following objective, "
            "produce a JSON plan with 2-5 steps.\n\n"
            f"Objective: {objective}\n"
            f"Context hints: {hints_str}\n\n"
            "Respond with ONLY valid JSON in this exact format:\n"
            '{"steps": [{"name": "...", "description": "...", '
            '"capability": "research|cognition|memory", '
            '"input_payload": {"question": "..."}, '
            '"dependencies": []}]}\n'
            "Each dependency is the 0-based index of a prior step."
        )
        request = AIRequest(
            messages=[AIMessage(role="user", content=prompt)],
            temperature=0.3,
            max_tokens=1024,
        )
        response = self._gateway.generate(request)
        return self._parse_plan(response.content, objective)

    def _parse_plan(self, raw: str, objective: str) -> WorkPlan:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        data = json.loads(text)
        if "steps" not in data or not isinstance(data["steps"], list):
            raise ValueError("Missing or invalid 'steps' key")
        if len(data["steps"]) == 0 or len(data["steps"]) > 10:
            raise ValueError("Plan must have 1-10 steps")

        now = datetime.now(timezone.utc).isoformat()
        step_ids: list[str] = []
        steps: list[WorkStep] = []

        for i, s in enumerate(data["steps"]):
            sid = f"step_{uuid.uuid4().hex[:8]}"
            step_ids.append(sid)

            raw_deps = s.get("dependencies", [])
            deps: list[str] = []
            for d in raw_deps:
                if isinstance(d, int) and 0 <= d < i:
                    deps.append(step_ids[d])

            capability = s.get("capability", "cognition")
            if capability not in ("research", "cognition", "memory"):
                capability = "cognition"

            payload = (
                s.get("input_payload", {})
                if isinstance(s.get("input_payload"), dict)
                else {}
            )

            steps.append(
                WorkStep(
                    step_id=sid,
                    name=str(s.get("name", f"Step {i + 1}")),
                    description=str(s.get("description", "")),
                    capability=capability,
                    input_payload=payload,
                    dependencies=tuple(deps),
                )
            )

        return WorkPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            steps=tuple(steps),
            version=1,
            created_at=now,
            updated_at=now,
        )
