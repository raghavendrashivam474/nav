"""Activity mapping — S19.

Transforms structured backend WorkActivity logs into clean user-facing lines.
Adheres to spec §7: Drops internal/private reasoning, keeps 1-2 meaningful lines.
"""

from __future__ import annotations

from core.contracts.work import WorkActivity, WorkActivityType
from interfaces.interaction.contracts import InteractionActivity

# Allowed types to expose (non-reasoning, observable transitions)
_ALLOWED_ACTIVITIES = {
    WorkActivityType.WORK_CREATED,
    WorkActivityType.STEP_STARTED,
    WorkActivityType.STEP_COMPLETED,
    WorkActivityType.STEP_FAILED,
    WorkActivityType.INPUT_REQUESTED,
    WorkActivityType.INPUT_PROVIDED,
    WorkActivityType.WORK_PAUSED,
    WorkActivityType.WORK_RESUMED,
    WorkActivityType.WORK_CANCELLED,
    WorkActivityType.WORK_REDIRECTED,
    WorkActivityType.APPROVAL_REQUESTED,
    WorkActivityType.APPROVAL_GRANTED,
    WorkActivityType.APPROVAL_REJECTED,
    WorkActivityType.HUMAN_TAKEOVER,
    WorkActivityType.CONTROL_RETURNED,
}


def work_activity_to_interaction_activity(activity: WorkActivity) -> InteractionActivity | None:
    """Filter and map WorkActivity to InteractionActivity. Returns None if hidden."""
    if activity.activity_type not in _ALLOWED_ACTIVITIES:
        return None

    desc = activity.description
    # Format description slightly for cleaner user presentation
    if activity.activity_type == WorkActivityType.WORK_CREATED:
        desc = f"Goal initialized: {desc}"
    elif activity.activity_type == WorkActivityType.STEP_STARTED:
        desc = f"Running step: {desc.replace('Executing: ', '')}"
    elif activity.activity_type == WorkActivityType.STEP_COMPLETED:
        desc = f"Completed step: {desc.replace('Completed: ', '')}"

    return InteractionActivity(
        description=desc,
        timestamp=activity.timestamp,
        activity_type=activity.activity_type.value,
    )
