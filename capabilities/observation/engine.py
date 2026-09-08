"""
NAV v2 — S30: Observation Engine.

Executes the observation lifecycle: validation, observation via bounded
sources, and result construction. Deterministic with honest uncertainty.

Key principles:
- Observation is separate from Action. No automatic feedback loop.
- Unknown observations remain unknown.
- Bounded observation sources only.
- External content is data, not instructions.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from core.contracts.observation import (
    Observation,
    ObservationRequest,
    ObservationResult,
    ObservationSource,
    ObservationState,
)
from core.log import get_logger

logger = get_logger(__name__)

# Type alias for observation adapters.
ObservationAdapter = Callable[[ObservationRequest], dict[str, Any]]


def _echo_observation_adapter(request: ObservationRequest) -> dict[str, Any]:
    """ECHO observation adapter: returns parameters as observed state.

    Useful for testing the full observation lifecycle without real
    external state inspection. Mirrors S29's ECHO action adapter
    philosophy.
    """
    expected = str(request.parameters.get("expected_state", ""))
    if expected:
        return {
            "observed_state": expected,
            "state": ObservationState.OBSERVED,
            "provenance": "echo:direct_inspection",
        }
    return {
        "observed_state": "no expected state provided for echo observation",
        "state": ObservationState.UNKNOWN,
        "provenance": "echo:insufficient_parameters",
    }


def _make_state_check_adapter(
    registry: dict[str, Any],
) -> ObservationAdapter:
    """Factory for a state-check observation adapter.

    Checks an injectable state registry for the subject. The registry
    is a simple dict mapping subject names to their current state
    descriptions. This is a bounded, explicit observation source —
    not a general-purpose filesystem or network scanner.
    """

    def adapter(request: ObservationRequest) -> dict[str, Any]:
        subject = request.subject.strip()
        if subject in registry:
            value = registry[subject]
            return {
                "observed_state": str(value),
                "state": ObservationState.OBSERVED,
                "provenance": "state_check:local_registry",
            }
        return {
            "observed_state": f"subject '{subject}' not found in registry",
            "state": ObservationState.NOT_OBSERVED,
            "provenance": "state_check:local_registry",
        }

    return adapter


class ObservationEngine:
    """Engine managing the observation lifecycle.

    Orchestrates validation and observation through bounded, explicit
    observation sources. Does NOT trigger actions, does NOT learn,
    does NOT persist.
    """

    def __init__(
        self,
        state_registry: dict[str, Any] | None = None,
    ) -> None:
        self._state_registry = state_registry if state_registry is not None else {}
        self._adapters: dict[ObservationSource, ObservationAdapter] = {
            ObservationSource.DIRECT_INSPECTION: _echo_observation_adapter,
            ObservationSource.LOCAL_STATE: _make_state_check_adapter(self._state_registry),
        }

    # ------------------------------------------------------------------
    # Full lifecycle
    # ------------------------------------------------------------------

    def observe(self, request: ObservationRequest) -> ObservationResult:
        """Run the full observation lifecycle: validate -> observe."""
        observation_id = str(uuid4())

        # 1. Validate
        validation_error = self._validate(request)
        if validation_error:
            return ObservationResult(
                observation_id=observation_id,
                subject=request.subject,
                state=ObservationState.INVALID,
                observation=None,
                message=f"Validation failed: {validation_error}",
            )

        # 2. Observe
        return self._observe(observation_id, request)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _validate(self, request: ObservationRequest) -> str | None:
        """Structural validation of the observation request."""
        if not isinstance(request.source, ObservationSource):
            return f"Unsupported observation source: {request.source!r}"
        if not request.subject or not request.subject.strip():
            return "Observation subject must not be empty."
        return None

    def _observe(
        self,
        observation_id: str,
        request: ObservationRequest,
    ) -> ObservationResult:
        """Perform the observation via the appropriate adapter."""
        adapter = self._adapters.get(request.source)
        now = datetime.now(timezone.utc)

        if adapter is None:
            # No adapter for this source — honest unknown.
            observation = Observation(
                observation_id=observation_id,
                source=request.source,
                subject=request.subject,
                observed_state=("no observation adapter available for source"),
                state=ObservationState.UNKNOWN,
                observed_at=now,
                action_id=request.action_id,
                provenance=(f"engine:no_adapter_for_{request.source.value}"),
            )
            return ObservationResult(
                observation_id=observation_id,
                subject=request.subject,
                state=ObservationState.UNKNOWN,
                observation=observation,
                message=(f"No observation adapter for source: {request.source.value}"),
                observed_at=now,
            )

        try:
            raw = adapter(request)
            observed_state = str(raw.get("observed_state", "unknown"))
            state = raw.get("state", ObservationState.UNKNOWN)
            if not isinstance(state, ObservationState):
                state = ObservationState.UNKNOWN
            provenance = str(raw.get("provenance", ""))

            observation = Observation(
                observation_id=observation_id,
                source=request.source,
                subject=request.subject,
                observed_state=observed_state,
                state=state,
                observed_at=now,
                action_id=request.action_id,
                provenance=provenance,
            )
            return ObservationResult(
                observation_id=observation_id,
                subject=request.subject,
                state=state,
                observation=observation,
                message=f"Observation completed: {state.value}",
                observed_at=now,
            )
        except Exception as exc:
            logger.error("Observation error for %s: %s", request.subject, exc)
            observation = Observation(
                observation_id=observation_id,
                source=request.source,
                subject=request.subject,
                observed_state="observation failed due to adapter error",
                state=ObservationState.UNKNOWN,
                observed_at=now,
                action_id=request.action_id,
                provenance="engine:adapter_exception",
            )
            return ObservationResult(
                observation_id=observation_id,
                subject=request.subject,
                state=ObservationState.UNKNOWN,
                observation=observation,
                message=f"Observation failed: {exc!s}",
                observed_at=now,
            )
