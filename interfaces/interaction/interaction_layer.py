"""Interaction Layer Boundary — S19.

Exposes the primary high-level API. Orchestrates commands, focus resolution,
cognition dispatching, control adaptations, state/activity mappings, and outputs.
"""

from __future__ import annotations

import uuid
from typing import Any

from core.contracts.capability import Request, Response
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.activity_mapping import work_activity_to_interaction_activity
from interfaces.interaction.commands import CommandInterpreter
from interfaces.interaction.contracts import (
    InteractionActivity,
    InteractionInput,
    InteractionOutput,
    InteractionOutputKind,
    NAVInteractionState,
    UserAction,
)
from interfaces.interaction.session import InteractionSession
from interfaces.interaction.state_mapping import work_status_to_interaction_state
from interfaces.interaction.work_control import WorkControlAdapter


class InteractionLayer:
    """The unified voice/text boundary layer over NAV's capability suite."""

    def __init__(
        self,
        orchestrator: Orchestrator,
        session: InteractionSession | None = None,
        default_capability: str = "cognition",
    ) -> None:
        self._orchestrator = orchestrator
        self._session = session or InteractionSession()
        self._interpreter = CommandInterpreter()
        self._control_adapter = WorkControlAdapter(orchestrator)
        self._default_capability = default_capability

    @property
    def session(self) -> InteractionSession:
        return self._session

    def process_input(self, user_input: InteractionInput) -> InteractionOutput:
        """Process text/voice inputs. Resolves commands, dispatches and maps response."""
        self._session.is_listening = False
        self._session.is_thinking = True

        interpreted = self._interpreter.interpret(user_input.text)

        try:
            if interpreted.action == UserAction.SEND_MESSAGE:
                return self._handle_conversation(user_input)
            else:
                return self._handle_control_action(interpreted.action, interpreted.payload)
        finally:
            self._session.is_thinking = False

    def get_presence_state(self) -> NAVInteractionState:
        """Derive the baseline state from session and backend signals."""
        if self._session.is_listening:
            return NAVInteractionState.LISTENING
        if self._session.is_thinking:
            return NAVInteractionState.THINKING
        if self._session.is_speaking:
            return NAVInteractionState.RESPONDING

        # Resolve status from active Work
        if self._session.focused_work_id:
            status_resp = self._get_work_status(self._session.focused_work_id)
            if status_resp.success:
                from core.contracts.work import WorkStatus

                raw_status = WorkStatus(status_resp.data.get("status", "pending"))
                return work_status_to_interaction_state(raw_status)

        return NAVInteractionState.IDLE

    # ------------------------------------------------------------------
    # Dispatch Handlers
    # ------------------------------------------------------------------

    def _handle_conversation(self, user_input: InteractionInput) -> InteractionOutput:
        """Dispatch clean conversational inputs to Cognition/Memory."""
        req_id = f"conv_{uuid.uuid4().hex[:8]}"

        payload: dict[str, Any] = {"prompt": user_input.text}

        target_cap = self._default_capability
        text_lower = user_input.text.lower()
        if "research" in text_lower or "investigate" in text_lower:
            target_cap = "research"
            payload = {"question": user_input.text}

        # If we have focused work and we are waiting for input, default to provide_input
        if self._session.focused_work_id:
            status_resp = self._get_work_status(self._session.focused_work_id)
            if status_resp.success and status_resp.data.get("status") == "waiting_for_input":
                return self._handle_control_action(
                    UserAction.PROVIDE_INPUT,
                    {"input_data": {"value": user_input.text}},
                )

        # Dispatch standard conversation flow
        request = Request(request_id=req_id, payload=payload)
        response = self._orchestrator.route_request(target_cap, request)

        # End thinking phase before evaluating presence state
        self._session.is_thinking = False

        if not response.success:
            return InteractionOutput(
                kind=InteractionOutputKind.ERROR,
                utterance=f"Something went wrong: {response.error}",
                interaction_state=NAVInteractionState.ERROR,
            )

        reply = str(response.data.get("reply", "I processed your request.")).strip()

        # Handle automatic work-focus synchronization if cognition spawned a work item
        work_id = response.data.get("work_id")
        if work_id:
            self._session.focused_work_id = str(work_id)

        activities = self._build_activity_strip()

        return InteractionOutput(
            kind=InteractionOutputKind.SPEAK,
            utterance=reply,
            interaction_state=self.get_presence_state(),
            focused_work_id=self._session.focused_work_id,
            activity_strip=activities,
        )

    def _handle_control_action(
        self, action: UserAction, payload: dict[str, Any]
    ) -> InteractionOutput:
        """Execute explicit goal-control instructions."""
        work_id = self._session.focused_work_id

        if not work_id:
            self._session.is_thinking = False
            return InteractionOutput(
                kind=InteractionOutputKind.ERROR,
                utterance="There is no active goal context to control right now.",
                interaction_state=NAVInteractionState.IDLE,
            )

        # Retrieve metadata context to resolve steps if approving/rejecting/inputting
        if action in (UserAction.APPROVE, UserAction.REJECT, UserAction.PROVIDE_INPUT):
            status_resp = self._get_work_status(work_id)
            if status_resp.success:
                if "step_id" not in payload:
                    step_id = status_resp.data.get("current_step_id") or "step_1"
                    payload["step_id"] = step_id

        # Dispatch via Control Adapter
        response = self._control_adapter.execute_control(action, work_id, payload)

        # End thinking phase before evaluating presence state
        self._session.is_thinking = False

        if not response.success:
            return InteractionOutput(
                kind=InteractionOutputKind.ERROR,
                utterance=f"I couldn't perform that action: {response.error}",
                interaction_state=self.get_presence_state(),
                focused_work_id=work_id,
            )

        ack_utterance = self._format_control_ack(action, response)
        activities = self._build_activity_strip()

        return InteractionOutput(
            kind=InteractionOutputKind.CONTROL_ACK,
            utterance=ack_utterance,
            interaction_state=self.get_presence_state(),
            focused_work_id=work_id,
            activity_strip=activities,
        )

    # ------------------------------------------------------------------
    # State & Log Aggregators
    # ------------------------------------------------------------------

    def _get_work_status(self, work_id: str) -> Response:
        req_id = f"stat_{uuid.uuid4().hex[:8]}"
        req = Request(
            request_id=req_id,
            payload={"action": "status", "work_id": work_id, "include_activity": True},
        )
        return self._orchestrator.route_request("work", req)

    def _build_activity_strip(self) -> tuple[InteractionActivity, ...]:
        """Aggregate activities using extended status capabilities."""
        if not self._session.focused_work_id:
            return ()

        resp = self._get_work_status(self._session.focused_work_id)
        if not resp.success or "recent_activity" not in resp.data:
            return ()

        recent = resp.data["recent_activity"]
        from core.contracts.work import WorkActivity, WorkActivityType

        mapped: list[InteractionActivity] = []
        for raw in recent:
            try:
                act = WorkActivity(
                    timestamp=raw["timestamp"],
                    activity_type=WorkActivityType(raw["activity_type"]),
                    description=raw["description"],
                    step_id=raw.get("step_id"),
                    metadata=raw.get("metadata", {}),
                )
                m = work_activity_to_interaction_activity(act)
                if m:
                    mapped.append(m)
            except Exception:
                continue

        return tuple(mapped[:2])

    @staticmethod
    def _format_control_ack(action: UserAction, response: Response) -> str:
        """Generate humanized summaries for active control executions."""
        status = response.data.get("status", "")
        obj = response.data.get("objective", "updated goal")

        messages = {
            UserAction.PAUSE: "Understood. I have paused the active execution loop.",
            UserAction.RESUME: "Resuming the active workflow execution now.",
            UserAction.CANCEL: "Cancelled. I have terminated the active execution loop.",
            UserAction.APPROVE: "Approval registered. Continuing step execution.",
            UserAction.REJECT: "I have rejected that step and paused work for plan revision.",
            UserAction.PROVIDE_INPUT: "Input registered. Resuming step.",
            UserAction.TAKE_OVER: "I have registered human takeover. Standing by.",
            UserAction.RETURN_CONTROL: "Control returned. Resuming automated pipeline.",
            UserAction.REDIRECT: f"Goal redirected: Now focusing on '{obj}'.",
            UserAction.REQUEST_STATUS: f"Goal is currently: {status.upper()}.",
        }

        return messages.get(action, "Control command executed.")
