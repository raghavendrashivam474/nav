"""Presence state derivation — S19.

Converts derived NAVInteractionState to visual PresenceState.
Guarantees clean flow separations.
"""

from __future__ import annotations

from interfaces.interaction.contracts import NAVInteractionState
from interfaces.presence.contracts import PresenceState


def interaction_state_to_presence_state(state: NAVInteractionState) -> PresenceState:
    """Derive visual states directly from active interaction states."""
    mapping = {
        NAVInteractionState.IDLE: PresenceState.IDLE,
        NAVInteractionState.LISTENING: PresenceState.LISTENING,
        NAVInteractionState.THINKING: PresenceState.THINKING,
        NAVInteractionState.WORKING: PresenceState.WORKING,
        NAVInteractionState.WAITING_FOR_INPUT: PresenceState.WAITING_FOR_INPUT,
        NAVInteractionState.WAITING_FOR_APPROVAL: PresenceState.WAITING_FOR_APPROVAL,
        NAVInteractionState.PAUSED: PresenceState.PAUSED,
        NAVInteractionState.RESPONDING: PresenceState.RESPONDING,
        NAVInteractionState.COMPLETED: PresenceState.COMPLETED,
        NAVInteractionState.ERROR: PresenceState.ERROR,
    }
    return mapping.get(state, PresenceState.IDLE)
