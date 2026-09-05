import unittest

from core.contracts.work import WorkActivity, WorkActivityType
from interfaces.interaction.activity_mapping import work_activity_to_interaction_activity


class TestActivityMapping(unittest.TestCase):
    def test_allowed_observability_mapping(self) -> None:
        act = WorkActivity(
            timestamp="2026-09-06T12:00:00Z",
            activity_type=WorkActivityType.STEP_STARTED,
            description="Executing: Compare packaging costs",
        )
        mapped = work_activity_to_interaction_activity(act)
        self.assertIsNotNone(mapped)
        self.assertEqual(mapped.description, "Running step: Compare packaging costs")

    def test_unexposed_reasoning_mapping_ignored(self) -> None:
        # Private/internal CoT activities should be swallowed
        act = WorkActivity(
            timestamp="2026-09-06T12:00:00Z",
            activity_type=WorkActivityType.EVALUATION_PERFORMED,
            description="Private reasoning chain...",
        )
        mapped = work_activity_to_interaction_activity(act)
        self.assertIsNone(mapped)
