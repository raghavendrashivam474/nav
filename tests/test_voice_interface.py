"""End-to-end mocked voice pipeline tests.

Proves the S4 architectural claim: voice is *just another interface* into
the existing S1/S2/S3 pipeline. No hardware, no APIs, no external deps.

Pipeline under test:
    FakeMicrophone -> MockSTT -> Orchestrator -> Cognition -> MockTTS -> FakeSpeaker
"""

import unittest

from capabilities.cognition.cognition import CognitionCapability
from core.capabilities.registry import CapabilityRegistry
from core.contracts.ai import AIGateway, AIRequest, AIResponse
from core.orchestration.orchestrator import Orchestrator
from interfaces.voice.audio import AudioInput
from interfaces.voice.errors import MicrophoneError, STTError, TTSError
from interfaces.voice.interface import VoiceInterface
from interfaces.voice.microphone import FakeMicrophone
from interfaces.voice.speaker import FakeSpeaker
from interfaces.voice.stt.mock_stt import MockSTT
from interfaces.voice.tts.mock_tts import MockTTS


class ScriptedAIGateway(AIGateway):
    """AI gateway that echoes the prompt back with a prefix. Deterministic."""

    def __init__(self, prefix: str = "NAV heard: ") -> None:
        self._prefix = prefix
        self.last_request: AIRequest | None = None

    def generate(self, request: AIRequest) -> AIResponse:
        self.last_request = request
        prompt = request.messages[-1].content
        return AIResponse(
            content=f"{self._prefix}{prompt}",
            model_used="scripted-model",
            usage={"prompt_tokens": len(prompt), "completion_tokens": 5, "total_tokens": 0},
        )


def _build_stack(
    *,
    transcript: str = "explain quantum tunneling",
    mic: FakeMicrophone | None = None,
    stt: MockSTT | None = None,
    tts: MockTTS | None = None,
    speaker: FakeSpeaker | None = None,
) -> tuple[VoiceInterface, ScriptedAIGateway, FakeSpeaker, MockTTS]:
    gateway = ScriptedAIGateway()
    cognition = CognitionCapability(gateway=gateway)
    registry = CapabilityRegistry()
    registry.register(cognition)
    orchestrator = Orchestrator(registry)

    _mic = mic or FakeMicrophone(
        AudioInput(samples=b"\x00" * 32, sample_rate=16000, duration_seconds=2.0)
    )
    _stt = stt or MockSTT(transcript=transcript)
    _tts = tts or MockTTS()
    _speaker = speaker or FakeSpeaker()

    voice = VoiceInterface(
        orchestrator=orchestrator,
        microphone=_mic,
        stt=_stt,
        tts=_tts,
        speaker=_speaker,
    )
    return voice, gateway, _speaker, _tts


class TestVoicePipelineHappyPath(unittest.TestCase):
    def test_full_cycle_succeeds(self) -> None:
        voice, _gw, speaker, tts = _build_stack(transcript="hello nav")
        response = voice.run_once(max_seconds=3.0)

        self.assertTrue(response.success, f"Expected success, got: {response.error}")
        self.assertIn("hello nav", response.data["reply"])
        self.assertEqual(len(tts.synthesize_calls), 1)
        self.assertEqual(len(speaker.played), 1)

    def test_voice_request_reaches_cognition_as_text_request(self) -> None:
        """The golden invariant: voice-originated request is indistinguishable
        from a text-originated request once it reaches Cognition."""
        voice, gateway, _speaker, _tts = _build_stack(transcript="what is entropy")
        voice.run_once()

        self.assertIsNotNone(gateway.last_request)
        assert gateway.last_request is not None
        self.assertEqual(gateway.last_request.messages[0].role, "user")
        self.assertEqual(gateway.last_request.messages[0].content, "what is entropy")

    def test_request_id_is_generated_and_prefixed(self) -> None:
        voice, _gw, _sp, _t = _build_stack()
        response = voice.run_once()
        self.assertTrue(response.request_id.startswith("voice_"))

    def test_tts_receives_cognition_reply_text(self) -> None:
        voice, _gw, _sp, tts = _build_stack(transcript="ping")
        voice.run_once()
        self.assertEqual(len(tts.synthesize_calls), 1)
        self.assertIn("ping", tts.synthesize_calls[0])


class TestVoicePipelineFailurePaths(unittest.TestCase):
    def test_microphone_failure_returns_graceful_error(self) -> None:
        voice, _gw, speaker, tts = _build_stack(
            mic=FakeMicrophone(raise_error=MicrophoneError("no mic")),
        )
        response = voice.run_once()
        self.assertFalse(response.success)
        self.assertIn("Microphone error", response.error or "")
        self.assertEqual(len(tts.synthesize_calls), 0)
        self.assertEqual(len(speaker.played), 0)

    def test_stt_failure_returns_graceful_error(self) -> None:
        voice, _gw, _sp, tts = _build_stack(
            stt=MockSTT(raise_error=STTError("engine dead")),
        )
        response = voice.run_once()
        self.assertFalse(response.success)
        self.assertIn("Transcription error", response.error or "")
        self.assertEqual(len(tts.synthesize_calls), 0)

    def test_empty_transcript_returns_graceful_error(self) -> None:
        voice, _gw, _sp, tts = _build_stack(stt=MockSTT(transcript="   "))
        response = voice.run_once()
        self.assertFalse(response.success)
        self.assertIn("No speech detected", response.error or "")
        self.assertEqual(len(tts.synthesize_calls), 0)

    def test_tts_failure_returns_graceful_error(self) -> None:
        voice, _gw, speaker, _tts = _build_stack(
            tts=MockTTS(raise_error=TTSError("engine dead")),
        )
        response = voice.run_once()
        self.assertFalse(response.success)
        self.assertIn("Voice output error", response.error or "")
        self.assertEqual(len(speaker.played), 0)

    def test_cognition_failure_is_propagated_and_spoken(self) -> None:
        """When cognition fails, voice should still try to inform the user."""

        class FailingGateway(AIGateway):
            def generate(self, request: AIRequest) -> AIResponse:
                raise RuntimeError("provider unreachable")

        cognition = CognitionCapability(gateway=FailingGateway())
        registry = CapabilityRegistry()
        registry.register(cognition)
        orchestrator = Orchestrator(registry)

        mic = FakeMicrophone(
            AudioInput(samples=b"\x00" * 32, sample_rate=16000, duration_seconds=1.0)
        )
        stt = MockSTT(transcript="hello")
        tts = MockTTS()
        speaker = FakeSpeaker()

        voice = VoiceInterface(orchestrator, mic, stt, tts, speaker)
        response = voice.run_once()

        self.assertFalse(response.success)
        # Voice should have attempted to speak the error to the user.
        self.assertEqual(len(tts.synthesize_calls), 1)


class TestVoicePipelineArchitecturalGuarantees(unittest.TestCase):
    def test_voice_uses_orchestrator_not_cognition_directly(self) -> None:
        """VoiceInterface must go through the Orchestrator."""
        import inspect

        from interfaces.voice import interface as voice_module

        source = inspect.getsource(voice_module)
        # It routes via orchestrator...
        self.assertIn("route_request", source)
        # ...and does not import Cognition directly.
        self.assertNotIn("CognitionCapability", source)
        self.assertNotIn("from capabilities", source)

    def test_voice_does_not_import_ai_providers(self) -> None:
        """VoiceInterface must not know about AI providers."""
        import inspect

        from interfaces.voice import interface as voice_module

        source = inspect.getsource(voice_module)
        self.assertNotIn("ollama", source.lower())
        self.assertNotIn("openai", source.lower())
        self.assertNotIn("from ai", source)


if __name__ == "__main__":
    unittest.main()
