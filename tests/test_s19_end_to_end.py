import unittest

from capabilities.cognition.cognition import CognitionCapability
from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.contracts.work import WorkStatus
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.contracts import (
    InteractionInput,
    InteractionInputKind,
    InteractionOutputKind,
    NAVInteractionState,
)
from interfaces.interaction.interaction_layer import InteractionLayer
from interfaces.interaction.session import InteractionSession


class EchoGateway(AIGateway):
    def generate(self, request: AIRequest) -> AIResponse:
        p = request.messages[-1].content
        return AIResponse(
            content=f"Processed: {p}",
            model_used="echo-model",
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        )


class TestEndToEndWorkflowControl(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = SQLiteWorkRepository(":memory:")
        self.service = WorkService(repository=self.repo)
        work_cap = WorkCapability(self.service)
        cog_cap = CognitionCapability(gateway=EchoGateway())

        registry = CapabilityRegistry()
        registry.register(work_cap)
        registry.register(cog_cap)

        self.orchestrator = Orchestrator(registry)
        self.session = InteractionSession()
        self.layer = InteractionLayer(self.orchestrator, self.session)

    def test_complete_human_control_cycle(self) -> None:
        # 1. Establish Work
        work = self.service.create_work("Explore system capabilities")
        self.service.auto_plan(work.work_id)
        self.session.focused_work_id = work.work_id

        # Verify initial visual state
        self.assertEqual(self.layer.get_presence_state(), NAVInteractionState.IDLE)

        # 2. User Pause action via Interaction layer
        user_input = InteractionInput(text="pause", kind=InteractionInputKind.TEXT)
        out = self.layer.process_input(user_input)

        self.assertEqual(out.kind, InteractionOutputKind.CONTROL_ACK)
        self.assertEqual(self.layer.get_presence_state(), NAVInteractionState.PAUSED)
        self.assertEqual(self.service.get_work(work.work_id).status, WorkStatus.PAUSED)

        # 3. User Resume action
        user_input = InteractionInput(text="resume", kind=InteractionInputKind.TEXT)
        out = self.layer.process_input(user_input)

        self.assertEqual(self.layer.get_presence_state(), NAVInteractionState.WORKING)
        self.assertEqual(self.service.get_work(work.work_id).status, WorkStatus.RUNNING)

        # 4. User Cancel action
        user_input = InteractionInput(text="cancel that", kind=InteractionInputKind.TEXT)
        out = self.layer.process_input(user_input)

        self.assertEqual(self.layer.get_presence_state(), NAVInteractionState.COMPLETED)
        self.assertEqual(self.service.get_work(work.work_id).status, WorkStatus.CANCELLED)
