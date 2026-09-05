import unittest

from capabilities.cognition.cognition import CognitionCapability
from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.contracts import (
    InteractionInput,
    InteractionInputKind,
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


class TestInteractionLayer(unittest.TestCase):
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

    def test_process_normal_conversation(self) -> None:
        user_input = InteractionInput(text="Hello NAV", kind=InteractionInputKind.TEXT)
        out = self.layer.process_input(user_input)

        self.assertTrue(out.utterance.startswith("Processed: Hello NAV"))
        self.assertEqual(out.interaction_state, NAVInteractionState.IDLE)

    def test_process_control_flow(self) -> None:
        work = self.service.create_work("Explore package alternatives")
        self.session.focused_work_id = work.work_id

        # Pause work
        self.service.auto_plan(work.work_id)
        user_input = InteractionInput(text="pause", kind=InteractionInputKind.TEXT)
        out = self.layer.process_input(user_input)

        self.assertEqual(out.interaction_state, NAVInteractionState.PAUSED)
        self.assertIn("paused", out.utterance)
