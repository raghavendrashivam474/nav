import unittest

from capabilities.cognition.cognition import CognitionCapability
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.orchestration.orchestrator import Orchestrator
from interfaces.interaction.interaction_layer import InteractionLayer
from interfaces.interaction.session import InteractionSession
from interfaces.voice.audio import AudioInput
from interfaces.voice.interaction_voice_adapter import InteractionVoiceAdapter
from interfaces.voice.microphone import FakeMicrophone
from interfaces.voice.speaker import FakeSpeaker
from interfaces.voice.stt.mock_stt import MockSTT
from interfaces.voice.tts.mock_tts import MockTTS


class ScriptedAIGateway(AIGateway):
    def __init__(self, prefix: str = "NAV heard: ") -> None:
        self._prefix = prefix

    def generate(self, request: AIRequest) -> AIResponse:
        prompt = request.messages[-1].content
        return AIResponse(
            content=f"{self._prefix}{prompt}",
            model_used="scripted-model",
            usage={"prompt_tokens": len(prompt), "completion_tokens": 5, "total_tokens": 0},
        )


class TestInteractionVoiceAdapter(unittest.TestCase):
    def test_voice_to_interaction_flow(self) -> None:
        gateway = ScriptedAIGateway()
        cog = CognitionCapability(gateway=gateway)
        registry = CapabilityRegistry()
        registry.register(cog)
        orchestrator = Orchestrator(registry)

        mic = FakeMicrophone(
            AudioInput(samples=b"\x00" * 32, sample_rate=16000, duration_seconds=1.0)
        )
        stt = MockSTT(transcript="Analyze quantum packaging models")
        tts = MockTTS()
        speaker = FakeSpeaker()

        session = InteractionSession()
        layer = InteractionLayer(orchestrator, session)
        adapter = InteractionVoiceAdapter(layer, mic, stt, tts, speaker)

        output = adapter.run_voice_cycle()

        self.assertIsNotNone(output)
        self.assertEqual(len(speaker.played), 1)
        self.assertIn("NAV heard: Analyze quantum packaging models", tts.synthesize_calls[0])
        self.assertEqual(session.focused_work_id, None)
