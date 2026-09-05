"""Presence interfaces package boundary — S19.

Exports PresenceState, PresenceFrame, and visual render contracts.
"""

from interfaces.presence.contracts import PresenceFrame, PresenceRenderer, PresenceState
from interfaces.presence.derivation import interaction_state_to_presence_state
from interfaces.presence.terminal_renderer import TerminalPresenceRenderer

__all__ = [
    "PresenceFrame",
    "PresenceRenderer",
    "PresenceState",
    "TerminalPresenceRenderer",
    "interaction_state_to_presence_state",
]
