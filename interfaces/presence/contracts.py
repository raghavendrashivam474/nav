"""Presence contracts — S19.

Defines the system visual state models and rendering protocols.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from interfaces.interaction.contracts import InteractionActivity


class PresenceState(str, Enum):
    """Visual rendering states communicating presence behavior (spec §12)."""

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


@dataclass(frozen=True)
class PresenceFrame:
    """An immutable rendering state snapshot representing active presence context."""

    state: PresenceState
    activity_strip: tuple[InteractionActivity, ...] = ()
    current_utterance: str | None = None
    focused_work_id: str | None = None


class PresenceRenderer(Protocol):
    """Common structural contract for all presence adapters."""

    def render(self, frame: PresenceFrame) -> None:
        """Express visual representation of system presence."""
        ...
