"""
NAV v2 — S29: Action Engine.

Executes the action lifecycle: validation, authorization, execution,
and result construction. Deterministic state machine with fail-closed
authorization.

Key principles:
- No action reaches external side effect without passing validation
  and authorization.
- State transitions are enforced by the contract-level state machine.
- Model output is untrusted; the engine never executes raw model
  suggestions.
- Execution adapters are explicit and bounded.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from core.contracts.action import (
    ActionOutcome,
    ActionRequest,
    ActionResult,
    ActionState,
    ActionType,
    is_valid_transition,
)
from core.contracts.security import (
    SYSTEM_ACTOR,
    ActorIdentity,
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
)
from core.log import get_logger

logger = get_logger(__name__)

# Type alias for the authorization function.
AuthorizerFn = Callable[[AuthorizationRequest], AuthorizationDecision]

# Type alias for execution adapters.
ExecutionAdapter = Callable[[ActionRequest], dict[str, Any]]


def _default_authorizer(req: AuthorizationRequest) -> AuthorizationDecision:
    """Fail-closed default authorizer.

    Allows SYSTEM_ACTOR (trust_level >= 100). Denies everything else.
    A real deployment should wire up a policy-driven authorizer.
    """
    if req.actor.trust_level >= 100:
        return AuthorizationDecision(
            outcome=AuthorizationOutcome.ALLOW,
            actor_id=req.actor.actor_id,
            action=req.action,
            resource=req.resource,
            reason="System actor with sufficient trust level.",
            policy_ref="s29:default:system-trust",
        )
    return AuthorizationDecision(
        outcome=AuthorizationOutcome.DENY,
        actor_id=req.actor.actor_id,
        action=req.action,
        resource=req.resource,
        reason="No policy grants this actor access to the requested action.",
        policy_ref="s29:default:fail-closed",
    )


def _echo_adapter(request: ActionRequest) -> dict[str, Any]:
    """ECHO adapter: returns parameters as result. No external side effects."""
    return {"echo": dict(request.parameters)}


def _log_adapter(request: ActionRequest) -> dict[str, Any]:
    """LOG adapter: records a structured log entry via NAV logging."""
    message = str(request.parameters.get("message", ""))
    level = str(request.parameters.get("level", "info")).lower()
    log_fn = getattr(logger, level, logger.info)
    log_fn("S29 Action LOG [%s]: %s", request.target, message)
    return {"logged": True, "target": request.target, "level": level}


class ActionEngine:
    """Engine managing the action lifecycle.

    Orchestrates validation, authorization, and execution through
    explicit state transitions.
    """

    _ADAPTERS: dict[ActionType, ExecutionAdapter] = {
        ActionType.ECHO: _echo_adapter,
        ActionType.LOG: _log_adapter,
    }

    def __init__(
        self,
        authorizer: AuthorizerFn | None = None,
    ) -> None:
        self._authorizer = authorizer or _default_authorizer

    # ------------------------------------------------------------------
    # Full lifecycle
    # ------------------------------------------------------------------

    def process(
        self,
        request: ActionRequest,
        actor: ActorIdentity | None = None,
    ) -> ActionResult:
        """Run the full action lifecycle: validate → authorize → execute."""
        action_id = str(uuid4())
        actor = actor or SYSTEM_ACTOR

        # 1. Validate
        validation_error = self._validate(request)
        if validation_error:
            return self._rejected(
                action_id, request, f"Validation failed: {validation_error}"
            )

        # 2. Authorize
        auth_decision = self._authorize(request, actor)
        if auth_decision.outcome != AuthorizationOutcome.ALLOW:
            return self._rejected(
                action_id,
                request,
                f"Authorization denied: {auth_decision.reason}",
            )

        # 3. Execute
        return self._execute(action_id, request)

    # ------------------------------------------------------------------
    # Individual lifecycle steps
    # ------------------------------------------------------------------

    def validate(self, request: ActionRequest) -> str | None:
        """Validate an action request. Returns error message or None."""
        return self._validate(request)

    def authorize(
        self,
        request: ActionRequest,
        actor: ActorIdentity,
    ) -> AuthorizationDecision:
        """Evaluate authorization for an action request."""
        return self._authorize(request, actor)

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _validate(self, request: ActionRequest) -> str | None:
        """Structural validation of the action request."""
        if not isinstance(request.action_type, ActionType):
            return f"Unsupported action type: {request.action_type!r}"
        if request.action_type not in self._ADAPTERS:
            return f"No execution adapter for action type: {request.action_type.value}"
        if not request.target or not request.target.strip():
            return "Action target must not be empty."
        return None

    def _authorize(
        self,
        request: ActionRequest,
        actor: ActorIdentity,
    ) -> AuthorizationDecision:
        """Construct an AuthorizationRequest and evaluate it."""
        auth_req = AuthorizationRequest(
            actor=actor,
            action=request.action_type.value,
            resource=request.target,
            context={"source": request.source},
        )
        try:
            return self._authorizer(auth_req)
        except Exception as exc:
            logger.error("Authorizer raised exception: %s", exc)
            return AuthorizationDecision(
                outcome=AuthorizationOutcome.DENY,
                actor_id=actor.actor_id,
                action=request.action_type.value,
                resource=request.target,
                reason=f"Authorizer error: {exc!s}",
                policy_ref="s29:error:fail-closed",
            )

    def _execute(
        self,
        action_id: str,
        request: ActionRequest,
    ) -> ActionResult:
        """Execute the action via the appropriate adapter."""
        adapter = self._ADAPTERS.get(request.action_type)
        if adapter is None:
            return ActionResult(
                action_id=action_id,
                action_type=request.action_type,
                state=ActionState.FAILED,
                outcome=ActionOutcome.FAILURE,
                message=f"No adapter for action type: {request.action_type.value}",
                target=request.target,
                executed_at=datetime.now(timezone.utc),
            )

        try:
            result_data = adapter(request)
            return ActionResult(
                action_id=action_id,
                action_type=request.action_type,
                state=ActionState.SUCCEEDED,
                outcome=ActionOutcome.SUCCESS,
                message=f"Action {request.action_type.value} completed successfully.",
                target=request.target,
                executed_at=datetime.now(timezone.utc),
                metadata={"result_data": result_data},
            )
        except Exception as exc:
            logger.error(
                "Action %s execution error: %s",
                request.action_type.value,
                exc,
            )
            return ActionResult(
                action_id=action_id,
                action_type=request.action_type,
                state=ActionState.FAILED,
                outcome=ActionOutcome.FAILURE,
                message=f"Execution failed: {exc!s}",
                target=request.target,
                executed_at=datetime.now(timezone.utc),
            )

    def _rejected(
        self,
        action_id: str,
        request: ActionRequest,
        reason: str,
    ) -> ActionResult:
        """Construct a REJECTED result."""
        return ActionResult(
            action_id=action_id,
            action_type=request.action_type,
            state=ActionState.REJECTED,
            outcome=ActionOutcome.REJECTION,
            message=reason,
            target=request.target,
        )
