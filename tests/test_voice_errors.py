"""Voice error hierarchy tests."""

import unittest

from interfaces.voice.errors import (
    ConfigurationError,
    MicrophoneError,
    PlaybackError,
    STTError,
    TTSError,
    VoiceError,
)


class TestErrorHierarchy(unittest.TestCase):
    def test_all_inherit_voice_error(self) -> None:
        for cls in (ConfigurationError, MicrophoneError, STTError, TTSError, PlaybackError):
            self.assertTrue(issubclass(cls, VoiceError), f"{cls.__name__} must inherit VoiceError")

    def test_voice_error_is_exception(self) -> None:
        self.assertTrue(issubclass(VoiceError, Exception))

    def test_can_be_caught_as_voice_error(self) -> None:
        with self.assertRaises(VoiceError):
            raise STTError("boom")


if __name__ == "__main__":
    unittest.main()
