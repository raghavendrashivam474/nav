import unittest

from core.contracts.work import WorkStatus
from interfaces.interaction.contracts import NAVInteractionState
from interfaces.interaction.state_mapping import work_status_to_interaction_state


class TestStateMapping(unittest.TestCase):
    def test_all_work_statuses_map_to_interaction_states(self) -> None:
        for status in WorkStatus:
            state = work_status_to_interaction_state(status)
            self.assertIsInstance(state, NAVInteractionState)

        self.assertEqual(
            work_status_to_interaction_state(WorkStatus.RUNNING),
            NAVInteractionState.WORKING,
        )
        self.assertEqual(
            work_status_to_interaction_state(WorkStatus.PAUSED),
            NAVInteractionState.PAUSED,
        )
        self.assertEqual(
            work_status_to_interaction_state(WorkStatus.WAITING_FOR_INPUT),
            NAVInteractionState.WAITING_FOR_INPUT,
        )
        self.assertEqual(
            work_status_to_interaction_state(WorkStatus.WAITING_FOR_APPROVAL),
            NAVInteractionState.WAITING_FOR_APPROVAL,
        )
