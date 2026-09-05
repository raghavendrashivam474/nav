"""Interaction contracts — S19.

Defines the types and structures for the human interaction layer.
Allows text and voice interfaces to communicate uniformly with NAV Core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InteractionInputKind(str, Enum):
    """Origin of user input."""

    TEXT = "text"
    VOICE = "voice"


class InteractionOutputKind(str, Enum):
    """Type of interaction response payload."""

    SPEAK = "speak"
    CONTROL_ACK = "control_ack"
    ERROR = "error"
    IDLE = "idle"


class NAVInteractionState(str, Enum):
    """Interaction-layer interpretation of overall system state."""

    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    PAUSED = "paused"
    RESPONDING = "responding"
    COMPLETED = "completed"
    ERROR = "error"


class UserAction(str, Enum):
    """Categorized human control or conversational action."""

    SEND_MESSAGE = "send_message"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"
    REDIRECT = "redirect"
    APPROVE = "approve"
    REJECT = "reject"
    PROVIDE_INPUT = "provide_input"
    TAKE_OVER = "take_over"
    RETURN_CONTROL = "return_control"
    REQUEST_STATUS = "request_status"


@dataclass(frozen=True)
class InteractionInput:
    """User utterance or explicit control action hitting the interaction boundary."""

    text: str
    kind: InteractionInputKind = InteractionInputKind.TEXT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InteractionActivity:
    """Human-readable description of current backend activity (no internal COT)."""

    description: str
    timestamp: str
    activity_type: str


@dataclass(frozen=True)
class InteractionOutput:
    """Consolidated interaction response sent to frontend/voice interfaces."""

    kind: InteractionOutputKind
    utterance: str
    interaction_state: NAVInteractionState
    focused_work_id: str | None = None
    activity_strip: tuple[InteractionActivity, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterpretedCommand:
    """Output of command interpretation parser."""

    action: UserAction
    payload: dict[str, Any] = field(default_factory=dict)
