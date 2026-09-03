"""Deterministic STT for tests. Zero dependencies."""

from __future__ import annotations

from interfaces.voice.audio import AudioInput
from interfaces.voice.contracts import SpeechToText
from interfaces.voice.errors import STTError


class MockSTT(SpeechToText):
    """Returns a pre-configured transcript. Optionally raises for failure tests."""

    def __init__(
        self,
        transcript: str = "hello nav",
        *,
        raise_error: STTError | None = None,
    ) -> None:
        self._transcript = transcript
        self._raise_error = raise_error
        self.transcribe_calls: list[AudioInput] = []

    @property
    def name(self) -> str:
        return "mock"

    def transcribe(self, audio: AudioInput) -> str:
        self.transcribe_calls.append(audio)
        if self._raise_error is not None:
            raise self._raise_error
        return self._transcript
