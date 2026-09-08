"""
NAV v2 — S29: Action Capability.

Implements the Capability interface for Orchestrator routing and Sx1
security enforcement.
"""

from __future__ import annotations

from typing import Any

from capabilities.action.engine import AuthorizerFn
from capabilities.action.service import ActionService
from core.contracts.action import ActionRequest, ActionType
from core.contracts.capability import Capability, Request, Response
from core.contracts.security import ActorIdentity, ActorType
from core.log import get_logger

logger = get_logger(__name__)


class ActionCapability(Capability):
    """Orchestrator-facing capability for authorized action execution.

    Actions:
    - execute: payload has "action_type", "target", optional
               "parameters", optional "requester_id", optional
               "source", optional "decision_id".
    """

    def __init__(
        self,
        service: ActionService | None = None,
        authorizer: AuthorizerFn | None = None,
    ) -> None:
        self._name = "action"
        self._version = "1.0.0"
        self._description = (
            "Explicit, inspectable, and authorized operation execution "
            "based on decisions or direct requests."
        )
        self._service = service or ActionService(authorizer=authorizer)

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return self._description

    @property
    def service(self) -> ActionService:
        return self._service

    def invoke(self, request: Request) -> Response:
        action = str(request.payload.get("action", "execute"))

        if action != "execute":
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Unknown action capability action: '{action}'",
            )

        try:
            return self._handle_execute(request.request_id, request.payload)
        except Exception as exc:
            logger.error("Action capability error: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Action failure: {exc!s}",
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_execute(
        self, request_id: str, payload: dict[str, Any]
    ) -> Response:
        # Parse action_type
        raw_type = str(payload.get("action_type", "")).strip()
        if not raw_type:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Action requires a non-empty 'action_type'.",
            )
        try:
            action_type = ActionType(raw_type)
        except ValueError:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=f"Unsupported action type: '{raw_type}'.",
            )

        # Parse target
        target = str(payload.get("target", "")).strip()
        if not target:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Action requires a non-empty 'target'.",
            )

        # Parse optional fields
        parameters = payload.get("parameters", {})
        if not isinstance(parameters, dict):
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="'parameters' must be a dict.",
            )

        requester_id = str(payload.get("requester_id", "")).strip()
        source = str(payload.get("source", "direct")).strip()
        decision_id = payload.get("decision_id")
        if decision_id is not None:
            decision_id = str(decision_id).strip()

        # Build ActionRequest
        try:
            action_request = ActionRequest(
                action_type=action_type,
                target=target,
                parameters=parameters,
                requester_id=requester_id,
                source=source,
                decision_id=decision_id,
                metadata=dict(payload.get("metadata", {})),
            )
        except ValueError as exc:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=f"Invalid action request: {exc!s}",
            )

        # Build actor from payload (default to SYSTEM_ACTOR)
        actor = self._build_actor(payload)

        # Execute
        result = self._service.execute(
            request=action_request,
            actor=actor,
        )

        return Response(
            request_id=request_id,
            data={"action_result": result},
            success=(result.state.value in ("succeeded",)),
        )

    def _build_actor(self, payload: dict[str, Any]) -> ActorIdentity:
        """Extract actor identity from payload if present."""
        actor_data = payload.get("actor")
        if isinstance(actor_data, ActorIdentity):
            return actor_data
        if isinstance(actor_data, dict):
            try:
                return ActorIdentity(
                    actor_id=str(actor_data.get("actor_id", "nav:system")),
                    actor_type=ActorType(
                        actor_data.get("actor_type", "system")
                    ),
                    trust_level=int(actor_data.get("trust_level", 0)),
                )
            except (ValueError, TypeError):
                pass
        from core.contracts.security import SYSTEM_ACTOR

        return SYSTEM_ACTOR
