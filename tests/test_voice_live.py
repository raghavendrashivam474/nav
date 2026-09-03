"""Live voice pipeline test ? gated by NAV_VOICE_LIVE=1.

Requires:
    - Voice extras installed:  pip install -e ".[voice]"
    - Working microphone + speakers
    - An Ollama instance running (or NAV_AI_PROVIDER=openai with key)

Run with:
    $env:NAV_VOICE_LIVE = "1"
    python -m unittest tests.test_voice_live
"""

import os
import unittest

RUN_LIVE = os.environ.get("NAV_VOICE_LIVE") == "1"


@unittest.skipUnless(RUN_LIVE, "Set NAV_VOICE_LIVE=1 to run the real voice test.")
class TestVoiceLive(unittest.TestCase):
    def test_press_speak_hear(self) -> None:
        from ai.gateway.default_gateway import DefaultAIGateway
        from capabilities.cognition.cognition import CognitionCapability
        from core.capabilities.registry import CapabilityRegistry
        from core.orchestration.orchestrator import Orchestrator
        from interfaces.voice.interface import VoiceInterface
        from interfaces.voice.microphone import Microphone
        from interfaces.voice.speaker import Speaker
        from interfaces.voice.stt.factory import create_stt
        from interfaces.voice.tts.factory import create_tts

        gateway = DefaultAIGateway()
        cognition = CognitionCapability(gateway=gateway)
        registry = CapabilityRegistry()
        registry.register(cognition)
        orchestrator = Orchestrator(registry)

        voice = VoiceInterface(
            orchestrator=orchestrator,
            microphone=Microphone(),
            stt=create_stt(),
            tts=create_tts(),
            speaker=Speaker(),
        )

        print("\n[NAV LIVE] Speak now (up to 8 seconds)...")
        response = voice.run_once(max_seconds=8.0)

        self.assertTrue(response.success, f"Failed: {response.error}")
        print(f"[NAV LIVE] Reply: {response.data.get('reply', '')[:200]}")


if __name__ == "__main__":
    unittest.main()
