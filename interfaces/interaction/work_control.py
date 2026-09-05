"""Work Control Adapter — S19.

Adapts high-level interaction UserActions into exact Capability Requests.
Dispatches directly via Orchestrator without importing WorkService.
"""

from __future__ import annotations

import uuid
from typing import Any

from core.contracts.capability import Request, Response
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.contracts import UserAction


class WorkControlAdapter:
    """Dispatches human actions directly to WorkCapability via Orchestrator."""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator

    def execute_control(
        self, action: UserAction, work_id: str, payload: dict[str, Any]
    ) -> Response:
        """Build and route standard capability requests."""
        req_id = f"ctrl_{uuid.uuid4().hex[:8]}"
        action_map = {
            UserAction.PAUSE: "pause",
            UserAction.RESUME: "resume",
            UserAction.CANCEL: "cancel",
            UserAction.APPROVE: "approve",
            UserAction.REJECT: "reject",
            UserAction.TAKE_OVER: "take_over",
            UserAction.RETURN_CONTROL: "return_control",
            UserAction.PROVIDE_INPUT: "provide_input",
            UserAction.REDIRECT: "redirect",
            UserAction.REQUEST_STATUS: "status",
        }

        action_str = action_map.get(action)
        if not action_str:
            return Response(
                request_id=req_id,
                success=False,
                error=f"Invalid control action: {action}",
            )

        # Assemble capability payload
        cap_payload: dict[str, Any] = {"action": action_str, "work_id": work_id}

        # Inject extra payload elements based on control demands
        if action == UserAction.PROVIDE_INPUT:
            cap_payload["input_data"] = payload.get("input_data", {})
            if "step_id" in payload:
                cap_payload["step_id"] = payload["step_id"]
        elif action == UserAction.REDIRECT:
            cap_payload["new_objective"] = payload.get("new_objective", "")
            if "steps" in payload:
                cap_payload["steps"] = payload["steps"]
        elif action in (UserAction.APPROVE, UserAction.REJECT):
            if "step_id" in payload:
                cap_payload["step_id"] = payload["step_id"]
            if "modified_payload" in payload:
                cap_payload["modified_payload"] = payload["modified_payload"]
            if "reason" in payload:
                cap_payload["reason"] = payload["reason"]

        request = Request(request_id=req_id, payload=cap_payload)
        return self._orchestrator.route_request("work", request)
