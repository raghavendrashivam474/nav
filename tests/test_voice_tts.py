"""MockTTS contract tests."""

import unittest

from interfaces.voice.contracts import TextToSpeech
from interfaces.voice.errors import TTSError
from interfaces.voice.tts.mock_tts import MockTTS


class TestMockTTS(unittest.TestCase):
    def test_implements_contract(self) -> None:
        self.assertIsInstance(MockTTS(), TextToSpeech)

    def test_produces_audio_output(self) -> None:
        tts = MockTTS()
        out = tts.synthesize("hello world")
        self.assertEqual(out.metadata["source_text"], "hello world")
        self.assertGreater(out.sample_rate, 0)

    def test_records_calls(self) -> None:
        tts = MockTTS()
        tts.synthesize("one")
        tts.synthesize("two")
        self.assertEqual(tts.synthesize_calls, ["one", "two"])

    def test_raises_when_configured_to_fail(self) -> None:
        tts = MockTTS(raise_error=TTSError("simulated"))
        with self.assertRaises(TTSError):
            tts.synthesize("hi")

    def test_has_name(self) -> None:
        self.assertEqual(MockTTS().name, "mock")


class TestTTSFactory(unittest.TestCase):
    def test_mock_provider_selectable(self) -> None:
        import os

        from interfaces.voice.tts.factory import create_tts

        prev = os.environ.get("NAV_TTS_PROVIDER")
        os.environ["NAV_TTS_PROVIDER"] = "mock"
        try:
            tts = create_tts()
            self.assertEqual(tts.name, "mock")
        finally:
            if prev is None:
                os.environ.pop("NAV_TTS_PROVIDER", None)
            else:
                os.environ["NAV_TTS_PROVIDER"] = prev

    def test_unknown_provider_raises(self) -> None:
        import os

        from interfaces.voice.errors import ConfigurationError
        from interfaces.voice.tts.factory import create_tts

        prev = os.environ.get("NAV_TTS_PROVIDER")
        os.environ["NAV_TTS_PROVIDER"] = "does-not-exist"
        try:
            with self.assertRaises(ConfigurationError):
                create_tts()
        finally:
            if prev is None:
                os.environ.pop("NAV_TTS_PROVIDER", None)
            else:
                os.environ["NAV_TTS_PROVIDER"] = prev


if __name__ == "__main__":
    unittest.main()
