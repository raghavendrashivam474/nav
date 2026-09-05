"""State mapping — S19.

Maps raw backend statuses into user-comprehensible interaction states.
Follows the spec mapping strictly.
"""

from __future__ import annotations

from core.contracts.work import WorkStatus
from interfaces.interaction.contracts import NAVInteractionState


def work_status_to_interaction_state(status: WorkStatus) -> NAVInteractionState:
    """Converts backend status into human interaction states."""
    mapping = {
        WorkStatus.PENDING: NAVInteractionState.IDLE,
        WorkStatus.PLANNING: NAVInteractionState.THINKING,
        WorkStatus.READY: NAVInteractionState.IDLE,
        WorkStatus.RUNNING: NAVInteractionState.WORKING,
        WorkStatus.PAUSED: NAVInteractionState.PAUSED,
        WorkStatus.COMPLETED: NAVInteractionState.COMPLETED,
        WorkStatus.FAILED: NAVInteractionState.ERROR,
        WorkStatus.BLOCKED: NAVInteractionState.ERROR,
        WorkStatus.CANCELLED: NAVInteractionState.COMPLETED,
        WorkStatus.WAITING_FOR_INPUT: NAVInteractionState.WAITING_FOR_INPUT,
        WorkStatus.WAITING_FOR_APPROVAL: NAVInteractionState.WAITING_FOR_APPROVAL,
    }
    return mapping.get(status, NAVInteractionState.IDLE)
