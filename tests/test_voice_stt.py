"""MockSTT contract tests."""

import unittest

from interfaces.voice.audio import AudioInput
from interfaces.voice.contracts import SpeechToText
from interfaces.voice.errors import STTError
from interfaces.voice.stt.mock_stt import MockSTT


class TestMockSTT(unittest.TestCase):
    def test_implements_contract(self) -> None:
        self.assertIsInstance(MockSTT(), SpeechToText)

    def test_returns_configured_transcript(self) -> None:
        stt = MockSTT(transcript="explain gravity")
        text = stt.transcribe(AudioInput(samples=b"", sample_rate=16000))
        self.assertEqual(text, "explain gravity")

    def test_records_calls(self) -> None:
        stt = MockSTT()
        audio = AudioInput(samples=b"", sample_rate=16000)
        stt.transcribe(audio)
        stt.transcribe(audio)
        self.assertEqual(len(stt.transcribe_calls), 2)

    def test_raises_when_configured_to_fail(self) -> None:
        stt = MockSTT(raise_error=STTError("simulated"))
        with self.assertRaises(STTError):
            stt.transcribe(AudioInput(samples=b"", sample_rate=16000))

    def test_has_name(self) -> None:
        self.assertEqual(MockSTT().name, "mock")


class TestSTTFactory(unittest.TestCase):
    def test_mock_provider_selectable(self) -> None:
        import os

        from interfaces.voice.stt.factory import create_stt

        prev = os.environ.get("NAV_STT_PROVIDER")
        os.environ["NAV_STT_PROVIDER"] = "mock"
        try:
            stt = create_stt()
            self.assertEqual(stt.name, "mock")
        finally:
            if prev is None:
                os.environ.pop("NAV_STT_PROVIDER", None)
            else:
                os.environ["NAV_STT_PROVIDER"] = prev

    def test_unknown_provider_raises(self) -> None:
        import os

        from interfaces.voice.errors import ConfigurationError
        from interfaces.voice.stt.factory import create_stt

        prev = os.environ.get("NAV_STT_PROVIDER")
        os.environ["NAV_STT_PROVIDER"] = "does-not-exist"
        try:
            with self.assertRaises(ConfigurationError):
                create_stt()
        finally:
            if prev is None:
                os.environ.pop("NAV_STT_PROVIDER", None)
            else:
                os.environ["NAV_STT_PROVIDER"] = prev


if __name__ == "__main__":
    unittest.main()
