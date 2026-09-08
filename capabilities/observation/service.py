"""
NAV v2 — S30: Observation Service Facade.

Primary service interface for the Observation subsystem. Coordinates
dispatch to the ObservationEngine.
"""

from __future__ import annotations

from typing import Any

from capabilities.observation.engine import ObservationEngine
from core.contracts.observation import ObservationRequest, ObservationResult


class ObservationService:
    """Subsystem facade for S30 Observation.

    Provides high-level entry points for performing observations.
    """

    def __init__(
        self,
        engine: ObservationEngine | None = None,
        state_registry: dict[str, Any] | None = None,
    ) -> None:
        self._engine = engine or ObservationEngine(state_registry=state_registry)

    @property
    def engine(self) -> ObservationEngine:
        return self._engine

    def observe(self, request: ObservationRequest) -> ObservationResult:
        """Observe the state of a subject.

        Args:
            request: The observation to perform.

        Returns:
            A frozen ObservationResult with full provenance.
        """
        return self._engine.observe(request)
