"""Interaction Interface package boundary — S19.

Exports core contracts and interaction implementation APIs.
"""

from interfaces.interaction.contracts import (
    InteractionActivity,
    InteractionInput,
    InteractionInputKind,
    InteractionOutput,
    InteractionOutputKind,
    InterpretedCommand,
    NAVInteractionState,
    UserAction,
)
from interfaces.interaction.interaction_layer import InteractionLayer
from interfaces.interaction.session import InteractionSession

__all__ = [
    "InteractionActivity",
    "InteractionInput",
    "InteractionInputKind",
    "InteractionOutput",
    "InteractionOutputKind",
    "InterpretedCommand",
    "NAVInteractionState",
    "UserAction",
    "InteractionLayer",
    "InteractionSession",
]
