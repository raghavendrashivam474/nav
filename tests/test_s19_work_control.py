import unittest

from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.contracts import UserAction
from interfaces.interaction.work_control import WorkControlAdapter


class TestWorkControlAdapter(unittest.TestCase):
    def setUp(self) -> None:
        repo = SQLiteWorkRepository(":memory:")
        self.service = WorkService(repository=repo)
        capability = WorkCapability(self.service)
        registry = CapabilityRegistry()
        registry.register(capability)
        self.orchestrator = Orchestrator(registry)
        self.adapter = WorkControlAdapter(self.orchestrator)

    def test_execute_control_pause_resume(self) -> None:
        work = self.service.create_work("Explore standard packaging mechanisms")
        work_id = work.work_id

        # Set standard status to active (running step) and execute plans to pause/resume
        self.service.auto_plan(work_id)

        # Run action pause
        resp = self.adapter.execute_control(UserAction.PAUSE, work_id, {})
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.get("status"), "paused")

        # Run action resume
        resp = self.adapter.execute_control(UserAction.RESUME, work_id, {})
        self.assertTrue(resp.success)
        self.assertEqual(resp.data.get("status"), "running")
