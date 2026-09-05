"""Interaction Session — S19.

Manages transient session focus and interface states like listening/thinking.
Is pure memory, does not persist to database, completely isolated from WorkService.
"""

from __future__ import annotations


class InteractionSession:
    """Transient state tracker for the current interaction session."""

    def __init__(self) -> None:
        self.focused_work_id: str | None = None
        self.is_listening: bool = False
        self.is_thinking: bool = False
        self.is_speaking: bool = False

    def reset(self) -> None:
        """Clear all session-scoped interaction properties."""
        self.focused_work_id = None
        self.is_listening = False
        self.is_thinking = False
        self.is_speaking = False
