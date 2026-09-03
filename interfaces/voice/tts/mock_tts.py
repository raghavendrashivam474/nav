"""Deterministic TTS for tests. Zero dependencies."""

from __future__ import annotations

from interfaces.voice.audio import AudioOutput
from interfaces.voice.contracts import TextToSpeech
from interfaces.voice.errors import TTSError


class MockTTS(TextToSpeech):
    """Produces a canned AudioOutput. Optionally raises for failure tests."""

    def __init__(
        self,
        *,
        raise_error: TTSError | None = None,
    ) -> None:
        self._raise_error = raise_error
        self.synthesize_calls: list[str] = []

    @property
    def name(self) -> str:
        return "mock"

    def synthesize(self, text: str) -> AudioOutput:
        self.synthesize_calls.append(text)
        if self._raise_error is not None:
            raise self._raise_error
        return AudioOutput(
            samples=text.encode("utf-8"),
            sample_rate=16000,
            channels=1,
            metadata={"source_text": text},
        )
