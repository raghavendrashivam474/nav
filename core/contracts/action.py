"""
NAV v2 — S29: Action Contracts.

Defines the structured action boundary. Represents explicit, inspectable,
and authorized operation execution based on decisions or direct requests.

Key Principles:
- S29 §6: No action reaches external side effect merely because an LLM
  suggested it.
- S29 §13: Action is separate from Decision. Decision selects; Action
  executes.
- S29 §17: Every externally meaningful action must pass through
  authorization.
- S29 §20: State machine is deterministic. Invalid transitions are
  rejected.
- S29 §23: Distinguish validation failure, authorization failure,
  execution failure, and indeterminate results.
- Frozen dataclasses enforce immutability across capability boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any


class ActionType(str, Enum):
    """Explicitly supported action types.

    This set is deliberately small and evidence-driven. New action types
    must be added through deliberate architectural decisions, not
    dynamically.

    ECHO: Return the input parameters as the result. No external side
          effects. Useful for testing the full action lifecycle.
    LOG:  Record a structured log entry via NAV's logging subsystem.
          The safest real side effect.
    """

    ECHO = "echo"
    LOG = "log"


class ActionState(str, Enum):
    """Lifecycle state of an action.

    REQUESTED:  Action has been submitted but not yet validated.
    VALIDATED:  Action structure and parameters are valid.
    AUTHORIZED: Authorization has been granted.
    EXECUTING:  Action is currently being performed.
    SUCCEEDED:  Action completed successfully with a known outcome.
    FAILED:     Action was attempted and a known failure occurred.
    REJECTED:   Action was rejected (validation or authorization).
    CANCELLED:  Action was cancelled before completion.
    UNKNOWN:    Action outcome is indeterminate (e.g. connection lost
                after the external system may have processed the request).
    """

    REQUESTED = "requested"
    VALIDATED = "validated"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ActionOutcome(str, Enum):
    """High-level outcome classification for action results.

    An exception is not always equivalent to failure — the external
    system may have processed the operation even if NAV lost the
    connection. This enum forces explicit classification.
    """

    SUCCESS = "success"
    FAILURE = "failure"
    REJECTION = "rejection"
    UNKNOWN = "unknown"


# Deterministic state machine. Maps each state to its valid successors.
VALID_TRANSITIONS: dict[ActionState, frozenset[ActionState]] = {
    ActionState.REQUESTED: frozenset({
        ActionState.VALIDATED,
        ActionState.REJECTED,
    }),
    ActionState.VALIDATED: frozenset({
        ActionState.AUTHORIZED,
        ActionState.REJECTED,
    }),
    ActionState.AUTHORIZED: frozenset({
        ActionState.EXECUTING,
        ActionState.REJECTED,
        ActionState.CANCELLED,
    }),
    ActionState.EXECUTING: frozenset({
        ActionState.SUCCEEDED,
        ActionState.FAILED,
        ActionState.UNKNOWN,
    }),
    # Terminal states — no further transitions.
    ActionState.SUCCEEDED: frozenset(),
    ActionState.FAILED: frozenset(),
    ActionState.REJECTED: frozenset(),
    ActionState.CANCELLED: frozenset(),
    ActionState.UNKNOWN: frozenset(),
}


def is_valid_transition(current: ActionState, target: ActionState) -> bool:
    """Check whether a state transition is permitted by the lifecycle."""
    return target in VALID_TRANSITIONS.get(current, frozenset())


@dataclass(frozen=True)
class ActionRequest:
    """An explicit request to perform an operation.

    Attributes:
        action_type: The type of action to perform.
        target: What the action affects (resource identifier).
        parameters: Action-specific parameters (frozen after creation).
        requester_id: Identity of who/what requested the action.
        source: Origin of the request ('decision' or 'direct').
        decision_id: Optional link to an S28 DecisionResult.
        metadata: Optional extension data (frozen after creation).
    """

    action_type: ActionType
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    requester_id: str = ""
    source: str = "direct"
    decision_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.target or not self.target.strip():
            raise ValueError("ActionRequest.target must not be empty.")
        if self.source not in ("decision", "direct"):
            raise ValueError(
                f"ActionRequest.source must be 'decision' or 'direct', "
                f"got '{self.source}'."
            )
        if self.source == "decision" and not self.decision_id:
            raise ValueError(
                "ActionRequest with source='decision' must have a decision_id."
            )
        # Freeze mutable dicts (same pattern as security.py ActorIdentity)
        if not isinstance(self.parameters, MappingProxyType):
            object.__setattr__(
                self, "parameters", MappingProxyType(dict(self.parameters))
            )
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self, "metadata", MappingProxyType(dict(self.metadata))
            )


@dataclass(frozen=True)
class ActionResult:
    """The outcome of an action execution attempt.

    Attributes:
        action_id: Unique identifier for this action execution.
        action_type: The type of action that was attempted.
        state: Final lifecycle state.
        outcome: High-level outcome classification.
        message: Human-readable description of what happened.
        target: The resource that was (or was to be) affected.
        executed_at: When execution was attempted (None if rejected).
        metadata: Optional extension data (frozen after creation).
    """

    action_id: str
    action_type: ActionType
    state: ActionState
    outcome: ActionOutcome
    message: str
    target: str = ""
    executed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_id or not self.action_id.strip():
            raise ValueError("ActionResult.action_id must not be empty.")
        if not self.message or not self.message.strip():
            raise ValueError("ActionResult.message must not be empty.")
        # Enforce state-outcome consistency
        _STATE_OUTCOME_MAP = {
            ActionState.SUCCEEDED: ActionOutcome.SUCCESS,
            ActionState.FAILED: ActionOutcome.FAILURE,
            ActionState.REJECTED: ActionOutcome.REJECTION,
            ActionState.UNKNOWN: ActionOutcome.UNKNOWN,
        }
        expected = _STATE_OUTCOME_MAP.get(self.state)
        if expected is not None and self.outcome != expected:
            raise ValueError(
                f"ActionResult with state {self.state.value} must have "
                f"outcome {expected.value}, got {self.outcome.value}."
            )
        # Freeze metadata
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self, "metadata", MappingProxyType(dict(self.metadata))
            )
