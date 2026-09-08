"""
NAV v2 — S30: Observation Capability.

Implements the Capability interface for Orchestrator routing.
"""

from __future__ import annotations

from typing import Any

from capabilities.observation.service import ObservationService
from core.contracts.capability import Capability, Request, Response
from core.contracts.observation import (
    ObservationRequest,
    ObservationSource,
    ObservationState,
)
from core.log import get_logger

logger = get_logger(__name__)


class ObservationCapability(Capability):
    """Orchestrator-facing capability for structured observation.

    Actions:
    - observe: payload has "subject", "source", optional "action_id",
               optional "parameters", optional "requester_id".
    """

    def __init__(
        self,
        service: ObservationService | None = None,
        state_registry: dict[str, Any] | None = None,
    ) -> None:
        self._name = "observation"
        self._version = "1.0.0"
        self._description = (
            "Explicit, inspectable, and honest representation of what "
            "NAV can establish about external state or effects."
        )
        self._service = service or ObservationService(state_registry=state_registry)

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
    def service(self) -> ObservationService:
        return self._service

    def invoke(self, request: Request) -> Response:
        action = str(request.payload.get("action", "observe"))

        if action != "observe":
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=(f"Unknown observation capability action: '{action}'"),
            )

        try:
            return self._handle_observe(request.request_id, request.payload)
        except Exception as exc:
            logger.error("Observation capability error: %s", exc)
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Observation failure: {exc!s}",
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_observe(self, request_id: str, payload: dict[str, Any]) -> Response:
        subject = str(payload.get("subject", "")).strip()
        if not subject:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Observation requires a non-empty 'subject'.",
            )

        raw_source = str(payload.get("source", "")).strip()
        if not raw_source:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error="Observation requires a non-empty 'source'.",
            )

        try:
            source = ObservationSource(raw_source)
        except ValueError:
            return Response(
                request_id=request_id,
                data={},
                success=False,
                error=f"Unsupported observation source: '{raw_source}'",
            )

        obs_request = ObservationRequest(
            subject=subject,
            source=source,
            action_id=payload.get("action_id"),
            parameters=payload.get("parameters", {}),
            requester_id=str(payload.get("requester_id", "")),
        )

        result = self._service.observe(obs_request)

        obs_data = None
        if result.observation is not None:
            obs = result.observation
            obs_data = {
                "observation_id": obs.observation_id,
                "source": obs.source.value,
                "subject": obs.subject,
                "observed_state": obs.observed_state,
                "state": obs.state.value,
                "action_id": obs.action_id,
                "provenance": obs.provenance,
            }

        return Response(
            request_id=request_id,
            data={
                "observation_id": result.observation_id,
                "subject": result.subject,
                "state": result.state.value,
                "message": result.message,
                "observed_at": (result.observed_at.isoformat() if result.observed_at else None),
                "observation": obs_data,
            },
            success=result.state != ObservationState.INVALID,
        )
