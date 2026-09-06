"""S19: Prove the additive include_activity extension to WorkCapability.status.

Two guarantees:
1. Legacy callers (no include_activity) get the exact S18 payload shape.
2. New callers (include_activity=True) get recent_activity in the response.
"""

import unittest

from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
from core.orchestration.orchestrator import Orchestrator


def _build_stack() -> tuple[WorkCapability, Orchestrator]:
    repo = SQLiteWorkRepository(":memory:")
    service = WorkService(repository=repo)
    cap = WorkCapability(service)
    registry = CapabilityRegistry()
    registry.register(cap)
    orchestrator = Orchestrator(registry)
    return cap, orchestrator


class TestStatusActivityExtension(unittest.TestCase):
    """Backward-compatible include_activity flag on WorkCapability.status."""

    def setUp(self) -> None:
        self.cap, self.orch = _build_stack()

    def _create_work(self) -> str:
        resp = self.cap.invoke(
            Request(request_id="c1", payload={"action": "create", "objective": "Test work"})
        )
        self.assertTrue(resp.success)
        return str(resp.data["work_id"])

    # ------------------------------------------------------------------
    # Legacy path — no include_activity
    # ------------------------------------------------------------------

    def test_legacy_status_payload_unchanged(self) -> None:
        """Without include_activity the payload matches S18 exactly."""
        wid = self._create_work()
        resp = self.cap.invoke(
            Request(request_id="s1", payload={"action": "status", "work_id": wid})
        )
        self.assertTrue(resp.success)
        expected_keys = {
            "work_id", "objective", "status", "current_step_id",
            "completed_steps", "pending_steps", "activity_count",
        }
        self.assertEqual(set(resp.data.keys()), expected_keys)
        self.assertNotIn("recent_activity", resp.data)

    def test_legacy_status_with_explicit_false(self) -> None:
        """include_activity=False must also omit recent_activity."""
        wid = self._create_work()
        resp = self.cap.invoke(
            Request(
                request_id="s2",
                payload={"action": "status", "work_id": wid, "include_activity": False},
            )
        )
        self.assertTrue(resp.success)
        self.assertNotIn("recent_activity", resp.data)

    # ------------------------------------------------------------------
    # New path — include_activity=True
    # ------------------------------------------------------------------

    def test_include_activity_returns_recent_entries(self) -> None:
        """With include_activity=True, recent_activity is present."""
        wid = self._create_work()
        resp = self.cap.invoke(
            Request(
                request_id="s3",
                payload={
                    "action": "status",
                    "work_id": wid,
                    "include_activity": True,
                },
            )
        )
        self.assertTrue(resp.success)
        self.assertIn("recent_activity", resp.data)
        activities = resp.data["recent_activity"]
        self.assertIsInstance(activities, list)
        # At minimum the WORK_CREATED activity should be present
        self.assertGreaterEqual(len(activities), 1)
        self.assertEqual(activities[0]["activity_type"], "work_created")

    def test_include_activity_respects_limit(self) -> None:
        """activity_limit caps the number of returned entries."""
        wid = self._create_work()
        # Plan + execute to generate more activity
        self.cap.invoke(
            Request(request_id="p1", payload={"action": "plan", "work_id": wid})
        )
        resp = self.cap.invoke(
            Request(
                request_id="s4",
                payload={
                    "action": "status",
                    "work_id": wid,
                    "include_activity": True,
                    "activity_limit": 1,
                },
            )
        )
        self.assertTrue(resp.success)
        self.assertEqual(len(resp.data["recent_activity"]), 1)

    def test_include_activity_newest_first(self) -> None:
        """Returned activities are in reverse-chronological order."""
        wid = self._create_work()
        self.cap.invoke(
            Request(request_id="p1", payload={"action": "plan", "work_id": wid})
        )
        resp = self.cap.invoke(
            Request(
                request_id="s5",
                payload={
                    "action": "status",
                    "work_id": wid,
                    "include_activity": True,
                    "activity_limit": 5,
                },
            )
        )
        self.assertTrue(resp.success)
        activities = resp.data["recent_activity"]
        self.assertGreaterEqual(len(activities), 2)
        # Newest first: plan_established should come before work_created
        types = [a["activity_type"] for a in activities]
        self.assertEqual(types[0], "plan_established")
        self.assertEqual(types[-1], "work_created")

    def test_include_activity_preserves_legacy_keys(self) -> None:
        """Legacy keys are still present when include_activity is True."""
        wid = self._create_work()
        resp = self.cap.invoke(
            Request(
                request_id="s6",
                payload={
                    "action": "status",
                    "work_id": wid,
                    "include_activity": True,
                },
            )
        )
        self.assertTrue(resp.success)
        for key in ("work_id", "objective", "status", "current_step_id",
                     "completed_steps", "pending_steps", "activity_count"):
            self.assertIn(key, resp.data)

    # ------------------------------------------------------------------
    # Via Orchestrator (the real dispatch path)
    # ------------------------------------------------------------------

    def test_orchestrator_status_with_activity(self) -> None:
        """The extension works through the Orchestrator dispatch path."""
        wid = self._create_work()
        resp = self.orch.route_request(
            "work",
            Request(
                request_id="s7",
                payload={
                    "action": "status",
                    "work_id": wid,
                    "include_activity": True,
                },
            ),
        )
        self.assertTrue(resp.success)
        self.assertIn("recent_activity", resp.data)


if __name__ == "__main__":
    unittest.main()

