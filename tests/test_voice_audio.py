"""AudioInput / AudioOutput value-object tests."""

import unittest

from interfaces.voice.audio import AudioInput, AudioOutput


class TestAudioInput(unittest.TestCase):
    def test_defaults(self) -> None:
        a = AudioInput(samples=b"abc", sample_rate=16000)
        self.assertEqual(a.channels, 1)
        self.assertIsNone(a.duration_seconds)
        self.assertEqual(a.metadata, {})

    def test_is_frozen(self) -> None:
        a = AudioInput(samples=b"abc", sample_rate=16000)
        with self.assertRaises(Exception):
            a.sample_rate = 8000  # type: ignore[misc]

    def test_carries_metadata(self) -> None:
        a = AudioInput(samples=b"", sample_rate=16000, metadata={"src": "test"})
        self.assertEqual(a.metadata["src"], "test")


class TestAudioOutput(unittest.TestCase):
    def test_defaults(self) -> None:
        a = AudioOutput(samples=b"abc", sample_rate=22050)
        self.assertEqual(a.channels, 1)
        self.assertEqual(a.metadata, {})

    def test_is_frozen(self) -> None:
        a = AudioOutput(samples=b"", sample_rate=16000)
        with self.assertRaises(Exception):
            a.channels = 2  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
