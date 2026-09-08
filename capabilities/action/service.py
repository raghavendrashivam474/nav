"""
NAV v2 — S29: Action Service Facade.

Primary service interface for the Action subsystem. Coordinates
authorization and dispatches to the ActionEngine.
"""

from __future__ import annotations

from capabilities.action.engine import ActionEngine, AuthorizerFn
from core.contracts.action import ActionRequest, ActionResult
from core.contracts.security import ActorIdentity, SYSTEM_ACTOR


class ActionService:
    """Subsystem facade for S29 Action.

    Provides high-level entry points for executing authorized actions.
    """

    def __init__(
        self,
        authorizer: AuthorizerFn | None = None,
        engine: ActionEngine | None = None,
    ) -> None:
        self._engine = engine or ActionEngine(authorizer=authorizer)

    @property
    def engine(self) -> ActionEngine:
        return self._engine

    def execute(
        self,
        request: ActionRequest,
        actor: ActorIdentity | None = None,
    ) -> ActionResult:
        """Execute an action through the full lifecycle.

        Args:
            request: The action to perform.
            actor: The identity requesting the action. Defaults to
                   SYSTEM_ACTOR for backward compatibility.

        Returns:
            A frozen ActionResult with full provenance.
        """
        return self._engine.process(
            request=request,
            actor=actor or SYSTEM_ACTOR,
        )
